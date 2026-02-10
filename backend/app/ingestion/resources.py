"""
Repair resources link generator connector.
Generates links to YouTube repair videos and Charm.li.
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink


class ResourcesConnector(BaseConnector):
    """YouTube + Charm.li repair resources link generator."""

    def __init__(self):
        super().__init__("resources")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate repair resource links."""
        encoded = quote_plus(query)
        encoded_replacement = quote_plus(f"{query} replacement")

        links = [
            ExternalLink(
                label=f"YouTube: '{query} replacement'",
                url=f"https://www.youtube.com/results?search_query={encoded_replacement}",
                source="youtube",
                category="repair_resources",
            ),
            ExternalLink(
                label=f"Charm.li: '{query}'",
                url=f"https://charm.li/?q={encoded}",
                source="charmli",
                category="repair_resources",
            ),
        ]

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
