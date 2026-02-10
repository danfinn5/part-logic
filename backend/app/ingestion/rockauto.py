"""
RockAuto link generator connector.
Generates search URLs for RockAuto's part number search.
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink
from app.utils.part_numbers import extract_part_numbers


class RockAutoConnector(BaseConnector):
    """RockAuto link generator (no scraping)."""

    def __init__(self):
        super().__init__("rockauto")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate RockAuto search links."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search RockAuto for '{query}'",
                url=f"https://www.rockauto.com/en/partsearch/?partnum={encoded}",
                source="rockauto",
                category="new_parts",
            )
        ]

        part_numbers = kwargs.get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"RockAuto: {pn}",
                url=f"https://www.rockauto.com/en/partsearch/?partnum={encoded_pn}",
                source="rockauto",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
