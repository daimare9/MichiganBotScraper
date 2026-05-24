"""Tests for ContractDatabase deduplication logic."""
import pytest

from src.database import ContractDatabase
from src.models import Contract


@pytest.fixture
def db(tmp_path) -> ContractDatabase:
    return ContractDatabase(db_path=str(tmp_path / "test.db"))


def test_new_contract_is_flagged_as_new(db, sample_contract):
    assert db.is_new(sample_contract) is True


def test_after_mark_seen_contract_is_not_new(db, sample_contract):
    db.mark_seen(sample_contract)
    assert db.is_new(sample_contract) is False


def test_different_source_same_id_are_independent(db):
    mdot = Contract("MDOT", "99-001", "Concrete job", "MDOT", "2026-01-01", "http://x")
    sigma = Contract("SIGMA", "99-001", "Concrete job", "SIGMA", "2026-01-01", "http://y")

    db.mark_seen(mdot)
    assert db.is_new(sigma) is True  # different source — independent key


def test_total_seen_count(db, sample_contract, sample_sigma_contract):
    assert db.total_seen() == 0
    db.mark_seen(sample_contract)
    assert db.total_seen() == 1
    db.mark_seen(sample_sigma_contract)
    assert db.total_seen() == 2


def test_mark_seen_is_idempotent(db, sample_contract):
    db.mark_seen(sample_contract)
    db.mark_seen(sample_contract)  # second call should not raise or duplicate
    assert db.total_seen() == 1


def test_unique_key_format(sample_contract):
    assert sample_contract.unique_key == "MDOT:26-1234"
