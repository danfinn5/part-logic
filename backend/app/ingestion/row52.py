"""
Row52 link generator connector.
Generates search URLs for Row52 salvage yard inventory.
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink
from app.config import settings


class Row52Connector(BaseConnector):
    """Row52 salvage yard link generator (no scraping)."""

    def __init__(self):
        super().__init__("row52")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Generate Row52 search links."""
        encoded = quote_plus(query)
        zip_code = kwargs.get("zip_code") or settings.carpart_default_zip or ""

        params = f"YMMorVIN={encoded}"
        if zip_code:
            params += f"&ZipCode={zip_code}&Distance=50"

        links = [
            ExternalLink(
                label=f"Search Row52 for '{query}'",
                url=f"https://row52.com/Search?{params}",
                source="row52",
                category="used_salvage",
            )
        ]

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
