import re
from abc import ABC, abstractmethod

from ..models import Contract


class BaseScraper(ABC):
    """All scrapers implement this interface."""

    SOURCE: str = ""

    def __init__(self, keywords: list[str]) -> None:
        # Pre-compile word-boundary patterns for each keyword (case-insensitive).
        # Multi-word keywords (e.g. "curb and gutter") are matched as phrases.
        self._patterns = [
            re.compile(r"\b" + re.escape(kw.lower()) + r"\b", re.IGNORECASE)
            for kw in keywords
        ]
        self.keywords = [k.lower() for k in keywords]

    def matches_keywords(self, text: str) -> bool:
        """Return True if *any* configured keyword appears in text as a whole word."""
        return any(p.search(text) for p in self._patterns)

    @abstractmethod
    def scrape(self) -> list[Contract]:
        """
        Perform a single scrape cycle.

        Returns a list of matching ``Contract`` objects.
        Must never raise — catch all exceptions internally and return [].
        """
