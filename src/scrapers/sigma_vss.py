"""
SIGMA VSS scraper
=================
Source  : https://sigma.michigan.gov/PRDVSS1X1/Advantage4
Strategy: Playwright (headless Chromium) — the site is a CGI Advantage 4
          JavaScript SPA.  We navigate the UI programmatically to reach the
          public solicitations listing, then filter by keywords.

What we scrape
--------------
* All *Open* solicitations visible without a login
* Filter by keyword match on solicitation title / description
* Return Contract objects ready for deduplication + email
"""

import logging
import re
from datetime import datetime
from typing import Optional

from playwright.sync_api import Browser, Page, sync_playwright

from ..models import Contract
from .base import BaseScraper

logger = logging.getLogger(__name__)

VSS_HOME = "https://sigma.michigan.gov/PRDVSS1X1/Advantage4"
# Maximum solicitations to scan per keyword to avoid run-away page loads
MAX_ROWS_PER_SCAN = 200


class SigmaVSSScraper(BaseScraper):
    SOURCE = "SIGMA"

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
            logger.error("SigmaVSSScraper failed: %s", exc, exc_info=True)
        logger.info("SIGMA: returned %d matching contract(s)", len(contracts))
        return contracts

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _run(self, browser: Browser) -> list[Contract]:
        context = browser.new_context(
            user_agent="Mozilla/5.0 (compatible; MichiganBotScraper/1.0; +https://github.com/)"
        )
        page = context.new_page()

        # Navigate to VSS home and wait for the SPA to boot
        page.goto(VSS_HOME, timeout=45_000, wait_until="networkidle")

        # Try to reach the public solicitations page
        solicitations_reached = self._navigate_to_solicitations(page)
        if not solicitations_reached:
            logger.warning("SIGMA: could not reach solicitations page — skipping")
            context.close()
            return []

        all_contracts: list[Contract] = []
        seen_keys: set[str] = set()

        # SIGMA VSS does not expose a keyword search without login.
        # We scan all visible open solicitations and filter client-side.
        page_contracts = self._extract_all_solicitations(page)
        logger.info(
            "SIGMA: found %d total solicitation(s) before keyword filter", len(page_contracts)
        )
        for c in page_contracts:
            if c.unique_key not in seen_keys and self.matches_keywords(
                f"{c.title} {c.description or ''}"
            ):
                seen_keys.add(c.unique_key)
                all_contracts.append(c)

        context.close()
        return all_contracts

    def _navigate_to_solicitations(self, page: Page) -> bool:
        """
        Attempt several strategies to reach the public solicitations list.
        Returns True if we land on a page that has solicitation data.
        """
        strategies = [
            # Menu click first — "View Published Solicitations" is always
            # visible on the home page and is the most reliable path.
            self._try_menu_click,
            self._try_direct_url,
        ]
        for strategy in strategies:
            try:
                if strategy(page):
                    return True
            except Exception as exc:
                logger.debug("SIGMA navigation strategy failed: %s", exc)
        return False

    def _try_direct_url(self, page: Page) -> bool:
        """Try known CGI Advantage 4 public-solicitation URL patterns."""
        # CGI Advantage 4 uses Angular hash routing — try hash variants first.
        # Alternate base paths observed in page source are also included.
        alt_base = "https://sigma.michigan.gov/PRDVSS1X1/advantage/Advantage4"
        candidates = [
            f"{VSS_HOME}/#/vsspublicpages/VSSPublicSolicitations",
            f"{VSS_HOME}/#/vsspublicpages/SolicListPage",
            f"{alt_base}/#/vsspublicpages/VSSPublicSolicitations",
            f"{alt_base}/#/vsspublicpages/SolicListPage",
        ]
        for url in candidates:
            try:
                page.goto(url, timeout=20_000, wait_until="networkidle")
                if self._has_solicitation_table(page):
                    logger.info("SIGMA: reached solicitations via direct URL: %s", url)
                    return True
            except Exception:
                continue
        return False

    def _try_menu_click(self, page: Page) -> bool:
        """Navigate from the VSS home page via the published-solicitations menu item."""
        page.goto(VSS_HOME, timeout=30_000, wait_until="networkidle")

        # Try various text selectors that SIGMA VSS might use
        link_texts = [
            "View Published Solicitations",
            "Published Solicitations",
            "Solicitations",
            "Open Bids",
            "Vendor Solicitations",
        ]
        for text in link_texts:
            try:
                locator = page.locator(f"text={text}").first
                if locator.is_visible(timeout=3_000):
                    locator.click()
                    # Angular SPA needs time to fetch and render the list
                    page.wait_for_load_state("networkidle", timeout=30_000)
                    try:
                        page.wait_for_selector(
                            "[class*='loading'], [class*='spinner']",
                            state="hidden",
                            timeout=5_000,
                        )
                    except Exception:
                        pass
                    if self._has_solicitation_table(page):
                        logger.info("SIGMA: reached solicitations by clicking '%s'", text)
                        return True
            except Exception:
                continue
        return False

    def _has_solicitation_table(self, page: Page) -> bool:
        """Heuristic: does this page look like a solicitations listing?"""
        # Reject if we're still on the home / login page
        if page.url.rstrip("/") in (
            VSS_HOME.rstrip("/"),
            VSS_HOME.rstrip("/") + "#",
        ):
            logger.debug("SIGMA: still on home page — navigation did not succeed")
            return False
        content = page.content().lower()
        signals = ["solicitation", "solicit", "bid", "rfp", "rfq", "itb", "proposal"]
        signal_count = sum(1 for s in signals if s in content)
        # Require >=3 hits AND actual list rows — the SIGMA 404/error page only
        # has 2 hits from the navigation bar, not a full solicitation listing.
        rows = page.query_selector_all("table tr, li")
        has_data = signal_count >= 3 and len(rows) > 5
        logger.debug(
            "SIGMA solicitation check: url=%s signals=%d rows=%d → %s",
            page.url, signal_count, len(rows), has_data,
        )
        return has_data

    def _extract_all_solicitations(self, page: Page) -> list[Contract]:
        """
        Extract solicitation rows from the current page (and paginate if possible).
        Stops after MAX_ROWS_PER_SCAN rows to stay well-behaved.
        """
        contracts: list[Contract] = []
        page_num = 0

        while len(contracts) < MAX_ROWS_PER_SCAN:
            page_num += 1
            batch = self._parse_current_page(page)
            contracts.extend(batch)
            logger.debug("SIGMA page %d: %d rows parsed", page_num, len(batch))

            if not self._go_to_next_page(page):
                break

        return contracts

    def _parse_current_page(self, page: Page) -> list[Contract]:
        """Extract all solicitation rows from the currently loaded page."""
        contracts: list[Contract] = []
        rows = page.query_selector_all("table tr")

        for row in rows:
            try:
                c = self._row_to_contract(row, page.url)
                if c:
                    contracts.append(c)
            except Exception as exc:
                logger.debug("SIGMA row error: %s", exc)

        # Fallback: look for list-item cards if the page uses a card layout
        if not contracts:
            contracts = self._parse_card_layout(page)

        return contracts

    def _row_to_contract(self, row, page_url: str) -> Optional[Contract]:
        cells = row.query_selector_all("td")
        if len(cells) < 2:
            return None

        values = [c.inner_text().strip() for c in cells]
        title = values[0] if values else ""
        if not title or title.lower() in ("solicitation", "title", "description", "#"):
            return None  # header row

        # Try to extract a solicitation number (typically a long numeric string)
        sol_number = _extract_solicitation_number(" ".join(values))
        if not sol_number:
            sol_number = _slugify(title)[:40]

        # Try to find a direct link
        link_el = row.query_selector("a")
        url = page_url
        if link_el:
            href = link_el.get_attribute("href") or ""
            if href:
                url = _resolve_sigma_url(href)

        agency = values[1] if len(values) > 1 else "State of Michigan"
        post_date_raw = _find_date_in_values(values) or datetime.now().strftime("%Y-%m-%d")
        close_date = _find_close_date(values)

        return Contract(
            source=self.SOURCE,
            contract_id=sol_number,
            title=title,
            agency=agency,
            post_date=post_date_raw,
            url=url,
            close_date=close_date,
            description=" | ".join(values[:5])[:500],
        )

    def _parse_card_layout(self, page: Page) -> list[Contract]:
        """
        Fallback parser for card/list-based UIs (Angular Material, etc.).
        Looks for repeated structural elements with solicitation info.
        """
        contracts: list[Contract] = []
        # Look for elements containing solicitation-like text patterns
        elements = page.query_selector_all("[class*='solicit'], [class*='bid'], [class*='card']")
        for el in elements:
            try:
                text = el.inner_text().strip()
                if not text or len(text) < 10:
                    continue
                sol_number = _extract_solicitation_number(text) or _slugify(text[:40])
                link_el = el.query_selector("a")
                url = VSS_HOME
                if link_el:
                    href = link_el.get_attribute("href") or ""
                    if href:
                        url = _resolve_sigma_url(href)
                contracts.append(
                    Contract(
                        source=self.SOURCE,
                        contract_id=sol_number,
                        title=text[:120],
                        agency="State of Michigan",
                        post_date=datetime.now().strftime("%Y-%m-%d"),
                        url=url,
                        description=text[:500],
                    )
                )
            except Exception:
                continue
        return contracts

    def _go_to_next_page(self, page: Page) -> bool:
        """Click a 'Next' pagination control if one exists. Return True on success."""
        next_selectors = [
            "text=Next",
            "text=Next »",
            "text=»",
            "[aria-label='Next page']",
            "button:has-text('Next')",
            "a:has-text('Next')",
        ]
        for sel in next_selectors:
            try:
                locator = page.locator(sel).first
                if locator.is_visible(timeout=2_000) and locator.is_enabled(timeout=2_000):
                    locator.click()
                    page.wait_for_load_state("networkidle", timeout=15_000)
                    return True
            except Exception:
                continue
        return False


# ── Utility helpers ────────────────────────────────────────────────────────── #

_SOL_NUMBER_RE = re.compile(r"\b\d{3}[A-Z]\d{7,}\b|\b[A-Z]{2}-\d{4}-\d+\b")

_DATE_RE = re.compile(
    r"\b(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|\w+ \d{1,2},\s*\d{4})\b"
)


def _extract_solicitation_number(text: str) -> Optional[str]:
    match = _SOL_NUMBER_RE.search(text)
    return match.group(0) if match else None


def _find_date_in_values(values: list[str]) -> Optional[str]:
    for v in values:
        m = _DATE_RE.search(v)
        if m:
            return m.group(0)
    return None


def _find_close_date(values: list[str]) -> Optional[str]:
    """Return the last date-like string found — typically the close date."""
    dates = []
    for v in values:
        for m in _DATE_RE.finditer(v):
            dates.append(m.group(0))
    return dates[-1] if len(dates) >= 2 else None


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _resolve_sigma_url(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return "https://sigma.michigan.gov" + href
    return VSS_HOME + "/" + href
