"""
Car-Part.com link generator connector.
Generates search URLs for Car-Part.com used auto parts.
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink
from app.config import settings


class CarPartConnector(BaseConnector):
    """Car-Part.com link generator."""

    def __init__(self):
        super().__init__("carpart")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate Car-Part.com search links."""
        zip_code = kwargs.get("zip_code") or settings.carpart_default_zip or ""
        encoded = quote_plus(query)

        url = f"https://www.car-part.com/search.htm?partDescription={encoded}"
        if zip_code:
            url += f"&zip={zip_code}"

        links = [
            ExternalLink(
                label=f"Search Car-Part.com for '{query}'",
                url=url,
                source="carpart",
                category="used_salvage",
            )
        ]

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
