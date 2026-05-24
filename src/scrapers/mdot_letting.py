"""
MDOT Bid Letting scraper
========================
Source  : http://mdotjboss.state.mi.us/BidLetting/BidLettingHome.htm
Strategy: Playwright (headless Chromium) — the site uses HTML frames and
          server-side page loads that Playwright handles cleanly.

What we scrape
--------------
* Upcoming & recently-posted letting dates from the left sidebar
* For each date: project list with contract ID, description, county, value
* Filter the list by keywords before returning
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page, sync_playwright

from ..models import Contract
from .base import BaseScraper

logger = logging.getLogger(__name__)

MDOT_HOME = "http://mdotjboss.state.mi.us/BidLetting/BidLettingHome.htm"
CCI_SEARCH = "https://mdotjboss.state.mi.us/CCI/home.htm"
# How many days back to include (catches newly posted ads for past lettings)
LOOKBACK_DAYS = 14


class MDOTLettingScraper(BaseScraper):
    SOURCE = "MDOT"

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def scrape(self) -> list[Contract]:
        contracts: list[Contract] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                contracts = self._run(browser)
                browser.close()
        except Exception as exc:
            logger.error("MDOTLettingScraper failed: %s", exc, exc_info=True)
        logger.info("MDOT: returned %d matching contract(s)", len(contracts))
        return contracts

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _run(self, browser: Browser) -> list[Contract]:
        context = browser.new_context(
            user_agent="Mozilla/5.0 (compatible; MichiganBotScraper/1.0; +https://github.com/)"
        )
        page = context.new_page()
        page.goto(MDOT_HOME, timeout=30_000, wait_until="networkidle")

        letting_links = self._collect_letting_links(page)
        logger.info("MDOT: found %d relevant letting date(s)", len(letting_links))

        contracts: list[Contract] = []
        for date_label, url in letting_links:
            try:
                page.goto(url, timeout=30_000, wait_until="networkidle")
                batch = self._parse_letting_page(page, date_label)
                contracts.extend(batch)
            except Exception as exc:
                logger.warning("MDOT: skipping letting %s — %s", date_label, exc)

        context.close()
        return contracts

    def _collect_letting_links(self, page: Page) -> list[tuple[str, str]]:
        """
        Collect upcoming letting dates from the MDOT home page.

        The MDOT site renders letting dates as submit-button inputs in the
        static HTML — no JavaScript needed:

            <input class="lettingButtons" type="submit"
                   title="2026-08-28"
                   onclick="window.location.assign(
                       'getLettingInfo.htm?letting=2026-08-28&index=0')">

        We fetch the page with requests (fast, no browser overhead) and
        extract dates from the ``title`` attribute and URLs from ``onclick``.
        A Playwright fallback is used if requests fails.
        """
        cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
        results: list[tuple[str, str]] = []

        _headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MichiganBotScraper/1.0)"
        }

        _onclick_re = re.compile(r"assign\(['\"]([^'\"]+)['\"]")

        def _extract_from_inputs(soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
            found: list[tuple[str, str]] = []
            for inp in soup.find_all("input", class_="lettingButtons"):
                title = inp.get("title", "").strip()   # "2026-08-28"
                onclick = inp.get("onclick", "")
                dt = _parse_date(title)
                if not dt or dt < cutoff:
                    continue
                m = _onclick_re.search(onclick)
                if m:
                    found.append((title, _resolve_url(base_url, m.group(1))))
            return found

        try:
            resp = requests.get(MDOT_HOME, timeout=15, headers=_headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            results = _extract_from_inputs(soup, MDOT_HOME)
            logger.info(
                "MDOT: found %d letting button(s) within the lookback window", len(results)
            )
        except Exception as exc:
            logger.warning(
                "MDOT: requests fetch failed (%s) — falling back to Playwright", exc
            )
            # Playwright fallback: apply the same selector on the rendered page
            for inp in (page.query_selector_all("input.lettingButtons") or []):
                try:
                    title = (inp.get_attribute("title") or "").strip()
                    onclick = inp.get_attribute("onclick") or ""
                    dt = _parse_date(title)
                    if not dt or dt < cutoff:
                        continue
                    m = _onclick_re.search(onclick)
                    if m:
                        results.append((title, _resolve_url(MDOT_HOME, m.group(1))))
                except Exception:
                    continue

        # De-duplicate by URL (home page may repeat the same letting)
        seen_urls: set[str] = set()
        unique: list[tuple[str, str]] = []
        for item in results:
            if item[1] not in seen_urls:
                seen_urls.add(item[1])
                unique.append(item)

        return unique

    def _parse_letting_page(self, page: Page, letting_date: str) -> list[Contract]:
        """Extract all keyword-matching projects from a letting detail page."""
        contracts: list[Contract] = []

        # The project list is populated asynchronously by a jqGrid AJAX call.
        # Wait up to 15 s for at least one row to appear inside #lettingBox.
        try:
            page.wait_for_selector("#lettingBox tr", state="attached", timeout=15_000)
        except Exception:
            logger.debug(
                "MDOT: #lettingBox grid did not appear within timeout for %s", letting_date
            )

        # The detail page typically renders inside a frame — check all frames
        frames_to_search = [page] + list(page.frames)
        for frame in frames_to_search:
            try:
                rows = frame.query_selector_all("table tr")
                if len(rows) > 1:
                    contracts = self._rows_to_contracts(rows, letting_date, page.url)
                    if contracts or len(rows) > 3:
                        break
            except Exception:
                continue

        return contracts

    def _rows_to_contracts(self, rows, letting_date: str, page_url: str) -> list[Contract]:
        contracts: list[Contract] = []
        for row in rows:
            try:
                cells = row.query_selector_all("td")
                if len(cells) < 2:
                    continue

                values = [c.inner_text().strip() for c in cells]
                full_text = " | ".join(values)

                if not self.matches_keywords(full_text):
                    continue

                contract_id = values[0] if values else "unknown"
                title = values[1] if len(values) > 1 else contract_id
                county = _first_or_none(values, 2)
                estimated_value = _first_or_none(values, 3)

                # Try to get a direct link from the first cell
                link_el = row.query_selector("a")
                url = page_url
                if link_el:
                    href = link_el.get_attribute("href") or ""
                    if href:
                        url = _resolve_url(MDOT_HOME, href)

                contracts.append(
                    Contract(
                        source=self.SOURCE,
                        contract_id=contract_id,
                        title=title,
                        agency="Michigan Dept of Transportation (MDOT)",
                        post_date=datetime.now().strftime("%Y-%m-%d"),
                        url=url,
                        county=county,
                        letting_date=letting_date,
                        estimated_value=estimated_value,
                        description=full_text[:500],
                    )
                )
            except Exception as exc:
                logger.debug("MDOT row parse error: %s", exc)
                continue

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
        # Absolute path relative to origin
        match = re.match(r"(https?://[^/]+)", base)
        origin = match.group(1) if match else "http://mdotjboss.state.mi.us"
        return origin + href
    # Relative path
    base_dir = base.rsplit("/", 1)[0]
    return base_dir + "/" + href


def _first_or_none(values: list[str], index: int) -> Optional[str]:
    if index < len(values) and values[index]:
        return values[index]
    return None
