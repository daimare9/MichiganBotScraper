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
