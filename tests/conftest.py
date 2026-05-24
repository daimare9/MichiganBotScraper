"""Shared pytest fixtures."""
import pytest

from src.models import Contract


@pytest.fixture
def sample_contract() -> Contract:
    return Contract(
        source="MDOT",
        contract_id="26-1234",
        title="CONCRETE PAVEMENT RESTORATION, WAYNE COUNTY",
        agency="Michigan Dept of Transportation (MDOT)",
        post_date="2026-05-23",
        url="http://mdotjboss.state.mi.us/BidLetting/BidLettingHome.htm",
        county="Wayne",
        letting_date="June 5, 2026",
        estimated_value="$1,200,000",
    )


@pytest.fixture
def sample_sigma_contract() -> Contract:
    return Contract(
        source="SIGMA",
        contract_id="255B7500218",
        title="Concrete Foundation Repair — State Capitol",
        agency="Department of Technology, Management and Budget",
        post_date="2026-05-20",
        url="https://sigma.michigan.gov/PRDVSS1X1/Advantage4",
        close_date="06/15/2026",
    )


@pytest.fixture
def concrete_keywords() -> list[str]:
    return ["concrete", "cement", "pavement", "slab", "foundation"]
