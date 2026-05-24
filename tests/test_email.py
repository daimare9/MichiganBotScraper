"""Tests for email HTML builder (no actual SMTP calls)."""

from src.email_sender import _build_html


def test_html_contains_contract_title(sample_contract, concrete_keywords):
    html = _build_html([sample_contract], concrete_keywords)
    assert "CONCRETE PAVEMENT RESTORATION" in html


def test_html_contains_view_bid_link(sample_contract, sample_sigma_contract, concrete_keywords):
    # MDOT contracts show "View PDF", SIGMA contracts show "View Solicitation"
    mdot_html = _build_html([sample_contract], concrete_keywords)
    assert "View PDF" in mdot_html
    assert sample_contract.url in mdot_html

    sigma_html = _build_html([sample_sigma_contract], concrete_keywords)
    assert "View Solicitation" in sigma_html
    assert sample_sigma_contract.url in sigma_html


def test_html_shows_correct_count(sample_contract, sample_sigma_contract, concrete_keywords):
    html = _build_html([sample_contract, sample_sigma_contract], concrete_keywords)
    assert "2 New Michigan Concrete Contracts Found" in html


def test_html_shows_mdot_badge(sample_contract, concrete_keywords):
    html = _build_html([sample_contract], concrete_keywords)
    assert "MDOT" in html


def test_html_shows_sigma_badge(sample_sigma_contract, concrete_keywords):
    html = _build_html([sample_sigma_contract], concrete_keywords)
    assert "SIGMA" in html


def test_html_shows_letting_date(sample_contract, concrete_keywords):
    html = _build_html([sample_contract], concrete_keywords)
    assert "June 5, 2026" in html


def test_html_shows_close_date(sample_sigma_contract, concrete_keywords):
    html = _build_html([sample_sigma_contract], concrete_keywords)
    assert "06/15/2026" in html


def test_html_shows_estimated_value(sample_contract, concrete_keywords):
    html = _build_html([sample_contract], concrete_keywords)
    assert "$1,200,000" in html


def test_html_shows_county(sample_contract, concrete_keywords):
    html = _build_html([sample_contract], concrete_keywords)
    assert "Wayne" in html


def test_html_is_valid_html(sample_contract, concrete_keywords):
    html = _build_html([sample_contract], concrete_keywords)
    assert html.strip().startswith("<!DOCTYPE html>")
    assert "</html>" in html
