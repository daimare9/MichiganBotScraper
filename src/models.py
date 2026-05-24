from dataclasses import dataclass
from typing import Optional


@dataclass
class Contract:
    """Represents a single construction contract or solicitation."""

    source: str          # "MDOT" | "SIGMA"
    contract_id: str     # Source-specific unique ID
    title: str           # Project/solicitation description
    agency: str          # Issuing agency name
    post_date: str       # ISO date string when the item was posted
    url: str             # Direct link to the bid/solicitation

    # Optional enrichment fields
    county: Optional[str] = None
    letting_date: Optional[str] = None    # MDOT: scheduled bid-opening date
    close_date: Optional[str] = None      # SIGMA: solicitation close date
    estimated_value: Optional[str] = None
    description: Optional[str] = None     # Raw text excerpt for context

    @property
    def unique_key(self) -> str:
        """Stable key used for deduplication in the database."""
        return f"{self.source}:{self.contract_id}"
