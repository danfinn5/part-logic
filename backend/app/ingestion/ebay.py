"""
eBay link generator connector.

Generates eBay search URLs for the user to browse directly.
eBay production API access requires business-level approval,
so this connector provides direct search links instead.
"""

from typing import Any
from urllib.parse import quote_plus

from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink


class eBayConnector(BaseConnector):
    """eBay link generator — builds search URLs for eBay."""

    def __init__(self):
        super().__init__("ebay")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Generate eBay search links for the given query."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search eBay for '{query}'",
                url=f"https://www.ebay.com/sch/i.html?_nkw={encoded}&_sacat=6028",
                source="ebay",
                category="new_parts",
            )
        ]

        for pn in kwargs.get("part_numbers") or []:
            encoded_pn = quote_plus(pn)
            links.append(
                ExternalLink(
                    label=f"eBay: {pn}",
                    url=f"https://www.ebay.com/sch/i.html?_nkw={encoded_pn}&_sacat=6028",
                    source="ebay",
                    category="new_parts",
                )
            )

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
