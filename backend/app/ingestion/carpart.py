"""
Car-Part.com connector.

Scrapes salvage yard search results from Car-Part.com.
Falls back to link generation on failure.
"""
import logging
from typing import Dict, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from app.ingestion.base import BaseConnector
from app.schemas.search import SalvageHit, ExternalLink
from app.config import settings
from app.utils.scraping import fetch_html
from app.utils.normalization import clean_url

logger = logging.getLogger(__name__)


class CarPartConnector(BaseConnector):
    """Car-Part.com salvage parts scraper with link fallback."""

    def __init__(self):
        super().__init__("carpart")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search Car-Part.com. Scrapes results when enabled, otherwise generates links."""
        zip_code = kwargs.get("zip_code") or settings.carpart_default_zip or ""

        if not settings.scrape_enabled:
            return self._generate_links(query, zip_code)

        try:
            results = await self._scrape(query, zip_code)
            results["external_links"] = [self._see_more_link(query, zip_code)]
            return results
        except Exception as e:
            logger.warning(f"Car-Part.com scrape failed: {e}")
            return self._generate_links(query, zip_code)

    async def _scrape(self, query: str, zip_code: str) -> Dict[str, Any]:
        """Fetch and parse Car-Part.com search results."""
        encoded = quote_plus(query)
        url = f"https://www.car-part.com/cgi-bin/search.cgi?userSearch=int&userPart={encoded}"
        if zip_code:
            url += f"&userZip={zip_code}"

        html, _ = await fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        salvage_hits = []
        # Car-Part.com uses table-based layout for results
        rows = soup.select("tr.resultsTable, table.resultsTable tr, tr[bgcolor]")
        if not rows:
            # Alternative: look for result rows by content pattern
            rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # Try to extract yard info, vehicle info, and part description
            text_content = [cell.get_text(strip=True) for cell in cells]
            link_tag = row.find("a", href=True)

            # Skip header/empty rows
            if not any(text_content) or all(t == "" for t in text_content):
                continue

            # Heuristic: look for rows with yard name, location, vehicle info
            yard_name = text_content[0] if len(text_content) > 0 else ""
            yard_location = text_content[1] if len(text_content) > 1 else ""
            vehicle = text_content[2] if len(text_content) > 2 else ""
            part_desc = text_content[3] if len(text_content) > 3 else query

            # Skip non-result rows
            if not yard_name or yard_name.lower() in ("yard", "location", "vehicle", ""):
                continue

            hit_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                hit_url = clean_url(href) if href else ""

            if yard_name and vehicle:
                salvage_hits.append(SalvageHit(
                    source="carpart",
                    yard_name=yard_name,
                    yard_location=yard_location,
                    vehicle=vehicle,
                    url=hit_url or f"https://www.car-part.com",
                    part_description=part_desc,
                ))

            if len(salvage_hits) >= settings.max_results_per_source:
                break

        return {
            "market_listings": [],
            "salvage_hits": salvage_hits,
            "external_links": [],
            "error": None,
        }

    def _generate_links(self, query: str, zip_code: str) -> Dict[str, Any]:
        """Generate Car-Part.com search links (fallback)."""
        encoded = quote_plus(query)
        url = f"https://www.car-part.com/search.htm?partDescription={encoded}"
        if zip_code:
            url += f"&zip={zip_code}"

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": [
                ExternalLink(
                    label=f"Search Car-Part.com for '{query}'",
                    url=url,
                    source="carpart",
                    category="used_salvage",
                )
            ],
            "error": None,
        }

    def _see_more_link(self, query: str, zip_code: str) -> ExternalLink:
        """Single 'see more' link for Car-Part.com."""
        encoded = quote_plus(query)
        url = f"https://www.car-part.com/search.htm?partDescription={encoded}"
        if zip_code:
            url += f"&zip={zip_code}"
        return ExternalLink(
            label="See all results on Car-Part.com",
            url=url,
            source="carpart",
            category="used_salvage",
        )
