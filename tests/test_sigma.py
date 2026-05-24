"""Unit tests for SIGMA VSS scraper helpers (no network calls)."""

from src.scrapers.sigma_vss import (
    SigmaVSSScraper,
    _extract_solicitation_number,
    _find_close_date,
    _find_date_in_values,
    _resolve_sigma_url,
)

# ── Keyword matching ──────────────────────────────────────────────────────── #

class TestKeywordMatching:
    def test_matches_foundation(self, concrete_keywords):
        scraper = SigmaVSSScraper(concrete_keywords)
        assert scraper.matches_keywords("Concrete Foundation Repair — State Capitol")

    def test_matches_slab(self, concrete_keywords):
        scraper = SigmaVSSScraper(concrete_keywords)
        assert scraper.matches_keywords("Parking Slab Replacement Project")

    def test_does_not_match_unrelated(self, concrete_keywords):
        scraper = SigmaVSSScraper(concrete_keywords)
        assert not scraper.matches_keywords("Office Furniture Procurement")


# ── Solicitation number extraction ────────────────────────────────────────── #

class TestSolicitationNumberExtraction:
    def test_extracts_standard_sigma_number(self):
        text = "Solicitation 255B7500218 — Facility Repair"
        assert _extract_solicitation_number(text) == "255B7500218"

    def test_returns_none_when_no_number(self):
        assert _extract_solicitation_number("No number here") is None


# ── Date helpers ─────────────────────────────────────────────────────────── #

class TestDateHelpers:
    def test_find_date_slash_format(self):
        result = _find_date_in_values(["Posted", "05/01/2026", "Agency"])
        assert result == "05/01/2026"

    def test_find_close_date_returns_last(self):
        result = _find_close_date(["05/01/2026", "06/15/2026"])
        assert result == "06/15/2026"

    def test_find_close_date_none_when_single(self):
        result = _find_close_date(["05/01/2026"])
        assert result is None


# ── URL resolution ────────────────────────────────────────────────────────── #

class TestSigmaUrlResolution:
    def test_absolute_url_unchanged(self):
        url = "https://sigma.michigan.gov/page"
        assert _resolve_sigma_url(url) == url

    def test_root_relative_prepends_sigma_origin(self):
        url = _resolve_sigma_url("/PRDVSS1X1/some/path")
        assert url == "https://sigma.michigan.gov/PRDVSS1X1/some/path"
