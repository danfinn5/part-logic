"""
Car-Part.com connector.

Car-Part.com requires structured searches: exact year + make/model + part
category from a 706-item predefined list, plus a two-step POST flow with
interchange selection. There is no free-text search URL.

This connector generates direct links to car-part.com. Real scraping would
require structured vehicle data (year, make, model) and a part-category
mapping layer, which is a future enhancement.
"""

import logging
from typing import Any

from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink

logger = logging.getLogger(__name__)


class CarPartConnector(BaseConnector):
    """Car-Part.com salvage parts link generator.

    Car-Part.com does not support free-text URL-based search.
    Searches require structured year/make/model/part-category via POST.
    """

    def __init__(self):
        super().__init__("carpart")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Generate Car-Part.com links. No scraping (requires structured POST)."""
        return self._generate_links(query)

    def _generate_links(self, query: str) -> dict[str, Any]:
        """Generate a link to Car-Part.com's main search page."""
        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": [
                ExternalLink(
                    label=f"Search Car-Part.com salvage yards for '{query}'",
                    url="https://www.car-part.com",
                    source="carpart",
                    category="used_salvage",
                )
            ],
            "error": None,
        }
