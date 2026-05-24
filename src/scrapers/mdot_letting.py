"""
MDOT Bid Letting scraper
========================
Source  : http://mdotjboss.state.mi.us/BidLetting/BidLettingHome.htm
Strategy: HTTP requests (no browser) — the letting list is in static HTML,
          and project descriptions are parsed from the Advertisements PDF
          (ads.pdf) that MDOT publishes for every letting date.

What we scrape
--------------
* Upcoming & recently-posted letting dates from the left sidebar
* For each date: fetches ads.pdf and extracts project descriptions
* Filters projects by keywords before returning
"""

import logging
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text as pdf_extract_text

from ..models import Contract
from .base import BaseScraper

logger = logging.getLogger(__name__)

MDOT_HOME = "http://mdotjboss.state.mi.us/BidLetting/BidLettingHome.htm"
BASE = "http://mdotjboss.state.mi.us/BidLetting"
# How many days back (and forward) to include letting dates
LOOKBACK_DAYS = 14

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MichiganBotScraper/1.0)"}

# Contract IDs appear as five-digit control section + six-digit project number
_CONTRACT_ID_RE = re.compile(r"\b(\d{5}-\d{6})\b")
_ONCLICK_RE = re.compile(r"assign\(['\"]([^'\"]+)['\"]")

# Matches "Description: <text>" up to the next project metadata field or EOF
_DESC_RE = re.compile(
    r"Description:\s*(.+?)(?=\nRequired|\nCompletion|\nNet Class|\nDate Advert|\nEstimated|\nCall Number|\Z)",
    re.DOTALL,
)


class MDOTLettingScraper(BaseScraper):
    SOURCE = "MDOT"

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def scrape(self) -> list[Contract]:
        contracts: list[Contract] = []
        try:
            contracts = self._run()
        except Exception as exc:
            logger.error("MDOTLettingScraper failed: %s", exc, exc_info=True)
        logger.info("MDOT: returned %d matching contract(s)", len(contracts))
        return contracts

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _run(self) -> list[Contract]:
        letting_links = self._collect_letting_links()
        logger.info("MDOT: found %d relevant letting date(s)", len(letting_links))
        contracts: list[Contract] = []
        for date_label, url in letting_links:
            try:
                batch = self._parse_letting_via_pdf(date_label, url)
                contracts.extend(batch)
            except Exception as exc:
                logger.warning("MDOT: skipping letting %s — %s", date_label, exc)
        return contracts

    def _collect_letting_links(self) -> list[tuple[str, str]]:
        """
        Collect letting dates from the MDOT home page.

        The MDOT site renders letting dates as submit-button inputs in the
        static HTML — no JavaScript needed:

            <input class="lettingButtons" type="submit"
                   title="2026-08-28"
                   onclick="window.location.assign(
                       'getLettingInfo.htm?letting=2026-08-28&index=0')">

        We fetch the page with requests and extract dates from the ``title``
        attribute and detail URLs from the ``onclick`` handler.
        """
        cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
        results: list[tuple[str, str]] = []

        try:
            resp = requests.get(MDOT_HOME, timeout=15, headers=_HEADERS)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for inp in soup.find_all("input", class_="lettingButtons"):
                title = inp.get("title", "").strip()   # "2026-08-28"
                onclick = inp.get("onclick", "")
                dt = _parse_date(title)
                if not dt or dt < cutoff:
                    continue
                m = _ONCLICK_RE.search(onclick)
                if m:
                    results.append((title, _resolve_url(MDOT_HOME, m.group(1))))
            logger.info(
                "MDOT: found %d letting button(s) within the lookback window", len(results)
            )
        except Exception as exc:
            logger.error("MDOT: failed to fetch letting list — %s", exc)
            return []

        # De-duplicate by URL (same letting may appear multiple times)
        seen: set[str] = set()
        unique: list[tuple[str, str]] = []
        for item in results:
            if item[1] not in seen:
                seen.add(item[1])
                unique.append(item)
        return unique

    def _parse_letting_via_pdf(self, letting_date: str, letting_url: str) -> list[Contract]:
        """Fetch the Advertisements PDF for a letting and return keyword-matching projects."""
        pdf_url = f"{BASE}/getFileByName.htm?fileName={letting_date}/ads.pdf"
        try:
            resp = requests.get(pdf_url, timeout=30, headers=_HEADERS)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("MDOT: could not fetch ads.pdf for %s — %s", letting_date, exc)
            return []

        try:
            text = pdf_extract_text(BytesIO(resp.content))
        except Exception as exc:
            logger.warning("MDOT: PDF extraction failed for %s — %s", letting_date, exc)
            return []

        return self._extract_projects_from_pdf(text, letting_date, letting_url)

    def _extract_projects_from_pdf(
        self, text: str, letting_date: str, letting_url: str
    ) -> list[Contract]:
        """Parse project description blocks from ads.pdf text and filter by keywords."""
        contracts: list[Contract] = []
        seen_ids: set[str] = set()

        for match in _DESC_RE.finditer(text):
            description = " ".join(match.group(1).split())  # normalize whitespace
            if not self.matches_keywords(description):
                continue

            # Find the nearest preceding contract ID (five-digit-six-digit pattern)
            preceding = text[: match.start()]
            id_matches = _CONTRACT_ID_RE.findall(preceding)
            contract_id = id_matches[-1] if id_matches else f"mdot-{letting_date}"

            if contract_id in seen_ids:
                continue
            seen_ids.add(contract_id)

            contracts.append(
                Contract(
                    source=self.SOURCE,
                    contract_id=contract_id,
                    title=f"MDOT Letting {letting_date} \u2014 {contract_id}",
                    agency="Michigan Dept of Transportation (MDOT)",
                    post_date=datetime.now().strftime("%Y-%m-%d"),
                    url=letting_url,
                    letting_date=letting_date,
                    description=description[:500],
                )
            )

        return contracts


# ── Utility helpers ────────────────────────────────────────────────────────── #

_DATE_FORMATS = (
    "%B %d, %Y",   # "May 6, 2026"
    "%m/%d/%Y",    # "05/06/2026"
    "%Y-%m-%d",    # "2026-05-06"
)


def _parse_date(text: str) -> Optional[datetime]:
    text = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _resolve_url(base: str, href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        match = re.match(r"(https?://[^/]+)", base)
        origin = match.group(1) if match else "http://mdotjboss.state.mi.us"
        return origin + href
    base_dir = base.rsplit("/", 1)[0]
    return base_dir + "/" + href

