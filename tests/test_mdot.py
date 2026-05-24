"""Unit tests for MDOT scraper helpers (no network calls)."""

from src.scrapers.mdot_letting import MDOTLettingScraper, _parse_date, _resolve_url

# ── Keyword matching ──────────────────────────────────────────────────────── #

class TestKeywordMatching:
    def test_matches_concrete(self, concrete_keywords):
        scraper = MDOTLettingScraper(concrete_keywords)
        assert scraper.matches_keywords("CONCRETE PAVEMENT RESTORATION")

    def test_matches_pavement(self, concrete_keywords):
        scraper = MDOTLettingScraper(concrete_keywords)
        assert scraper.matches_keywords("HMA Pavement and Bridge Work")

    def test_does_not_match_unrelated(self, concrete_keywords):
        scraper = MDOTLettingScraper(concrete_keywords)
        assert not scraper.matches_keywords("GUARDRAIL REPLACEMENT AND SIGNING")

    def test_case_insensitive(self, concrete_keywords):
        scraper = MDOTLettingScraper(concrete_keywords)
        assert scraper.matches_keywords("Concrete Curb And Gutter")
        assert scraper.matches_keywords("CEMENT TREATED BASE")


# ── Date parsing ──────────────────────────────────────────────────────────── #

class TestDateParsing:
    def test_parses_long_format(self):
        dt = _parse_date("May 6, 2026")
        assert dt is not None
        assert dt.month == 5
        assert dt.day == 6
        assert dt.year == 2026

    def test_parses_slash_format(self):
        dt = _parse_date("05/06/2026")
        assert dt is not None
        assert dt.month == 5

    def test_parses_iso_format(self):
        dt = _parse_date("2026-05-06")
        assert dt is not None
        assert dt.year == 2026

    def test_returns_none_for_garbage(self):
        assert _parse_date("Select a letting date") is None
        assert _parse_date("") is None
        assert _parse_date("Project ID") is None


# ── URL resolution ────────────────────────────────────────────────────────── #

class TestUrlResolution:
    BASE = "http://mdotjboss.state.mi.us/BidLetting/BidLettingHome.htm"

    def test_absolute_url_unchanged(self):
        url = "http://example.com/page.htm"
        assert _resolve_url(self.BASE, url) == url

    def test_root_relative_url(self):
        url = _resolve_url(self.BASE, "/BidLetting/getOneLetting.htm?id=1")
        assert url == "http://mdotjboss.state.mi.us/BidLetting/getOneLetting.htm?id=1"

    def test_relative_url(self):
        url = _resolve_url(self.BASE, "getOneLetting.htm?id=1")
        assert url == "http://mdotjboss.state.mi.us/BidLetting/getOneLetting.htm?id=1"


# ── PDF project extraction ────────────────────────────────────────────────── #

_SAMPLE_PDF_TEXT = """\
Call Number Contract ID Control Section Project Number
001 69021-215026 NH 69021 215026A
Description: 4.09 mi of concrete pavement rehabilitation and resurfacing on I-75.
Required DBE Participation: 0.00%
Completion Date: 9/23/2026
Date Advertised: 3/27/2026

002 82000-219011 NH 82000 219011A
Description: 0.69 mi of concrete shared-use path and concrete sidewalk ramps.
Required DBE Participation: 2.00%
Completion Date: 8/15/2026
Date Advertised: 3/27/2026

003 11000-220001 NH 11000 220001A
Description: 5.00 mi of guardrail replacement and signing only.
Required DBE Participation: 0.00%
Completion Date: 10/01/2026
Date Advertised: 3/27/2026
"""


class TestExtractProjectsFromPdf:
    def test_finds_concrete_project(self, concrete_keywords):
        scraper = MDOTLettingScraper(concrete_keywords)
        contracts = scraper._extract_projects_from_pdf(
            _SAMPLE_PDF_TEXT, "2026-06-05", "http://example.com/letting"
        )
        ids = [c.contract_id for c in contracts]
        assert "69021-215026" in ids   # bridge deck
        assert "82000-219011" in ids   # concrete sidewalk

    def test_skips_non_matching_project(self, concrete_keywords):
        scraper = MDOTLettingScraper(concrete_keywords)
        contracts = scraper._extract_projects_from_pdf(
            _SAMPLE_PDF_TEXT, "2026-06-05", "http://example.com/letting"
        )
        ids = [c.contract_id for c in contracts]
        assert "11000-220001" not in ids   # guardrail only

    def test_contract_fields_populated(self, concrete_keywords):
        scraper = MDOTLettingScraper(concrete_keywords)
        contracts = scraper._extract_projects_from_pdf(
            _SAMPLE_PDF_TEXT, "2026-06-05", "http://example.com/letting"
        )
        c = next(c for c in contracts if c.contract_id == "82000-219011")
        assert c.source == "MDOT"
        assert c.letting_date == "2026-06-05"
        assert c.url == "http://example.com/letting"
        assert "concrete" in c.description.lower()

    def test_no_duplicates(self, concrete_keywords):
        scraper = MDOTLettingScraper(concrete_keywords)
        # Repeat the text to simulate duplicate entries in PDF
        doubled = _SAMPLE_PDF_TEXT + _SAMPLE_PDF_TEXT
        contracts = scraper._extract_projects_from_pdf(
            doubled, "2026-06-05", "http://example.com/letting"
        )
        ids = [c.contract_id for c in contracts]
        assert len(ids) == len(set(ids))

