"""
PartsGeek link generator connector.
Generates search URLs for PartsGeek auto parts.
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink
from app.utils.part_numbers import extract_part_numbers


class PartsGeekConnector(BaseConnector):
    """PartsGeek link generator."""

    def __init__(self):
        super().__init__("partsgeek")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate PartsGeek search links."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search PartsGeek for '{query}'",
                url=f"https://www.partsgeek.com/search.html?query={encoded}",
                source="partsgeek",
                category="new_parts",
            )
        ]

        part_numbers = kwargs.get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"PartsGeek: {pn}",
                url=f"https://www.partsgeek.com/search.html?query={encoded_pn}",
                source="partsgeek",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
