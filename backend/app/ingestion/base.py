"""
Base connector interface for all ingestion sources.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Base class for all part search connectors."""

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """
        Search for parts using the given query.

        Returns a dict with keys:
        - "market_listings": List[MarketListing]
        - "salvage_hits": List[SalvageHit]
        - "external_links": List[ExternalLink]
        - "error": Optional[str] - error message if search failed
        """
        pass

    def get_cache_key(self, query: str) -> str:
        """Generate cache key for this source and query."""
        normalized = query.upper().strip().replace(" ", "_")
        return f"{self.source_name}:{normalized}"
