"""
ECS Tuning link generator connector.
Generates search URLs for European car parts (Audi/BMW/VW/Porsche/Mercedes/Mini).
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink
from app.utils.part_numbers import extract_part_numbers


class ECSTuningConnector(BaseConnector):
    """ECS Tuning link generator."""

    def __init__(self):
        super().__init__("ecstuning")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate ECS Tuning search links."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search ECS Tuning for '{query}'",
                url=f"https://www.ecstuning.com/Search/{encoded}/",
                source="ecstuning",
                category="new_parts",
            )
        ]

        part_numbers = kwargs.get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"ECS Tuning: {pn}",
                url=f"https://www.ecstuning.com/Search/{encoded_pn}/",
                source="ecstuning",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
