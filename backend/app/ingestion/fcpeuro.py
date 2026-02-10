"""
FCP Euro link generator connector.
Generates search URLs for European car parts with lifetime guarantee.
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink
from app.utils.part_numbers import extract_part_numbers


class FCPEuroConnector(BaseConnector):
    """FCP Euro link generator."""

    def __init__(self):
        super().__init__("fcpeuro")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate FCP Euro search links."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search FCP Euro for '{query}'",
                url=f"https://www.fcpeuro.com/search?query={encoded}",
                source="fcpeuro",
                category="new_parts",
            )
        ]

        part_numbers = kwargs.get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"FCP Euro: {pn}",
                url=f"https://www.fcpeuro.com/search?query={encoded_pn}",
                source="fcpeuro",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
