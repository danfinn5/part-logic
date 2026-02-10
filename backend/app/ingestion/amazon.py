"""
Amazon Automotive link generator connector.
Generates search URLs for Amazon's automotive parts category.
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink
from app.utils.part_numbers import extract_part_numbers


class AmazonConnector(BaseConnector):
    """Amazon Automotive link generator."""

    def __init__(self):
        super().__init__("amazon")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate Amazon Automotive search links."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search Amazon Automotive for '{query}'",
                url=f"https://www.amazon.com/s?k={encoded}&i=automotive-intl-ship",
                source="amazon",
                category="new_parts",
            )
        ]

        part_numbers = kwargs.get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"Amazon: {pn}",
                url=f"https://www.amazon.com/s?k={encoded_pn}&i=automotive-intl-ship",
                source="amazon",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
