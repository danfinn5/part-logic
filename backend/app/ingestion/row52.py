"""
Row52 salvage yard connector.

Scrapes salvage inventory search results from Row52.
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


class Row52Connector(BaseConnector):
    """Row52 salvage yard scraper with link fallback."""

    def __init__(self):
        super().__init__("row52")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search Row52. Scrapes results when enabled, otherwise generates links."""
        zip_code = kwargs.get("zip_code") or settings.carpart_default_zip or ""

        if not settings.scrape_enabled:
            return self._generate_links(query, zip_code)

        try:
            results = await self._scrape(query, zip_code)
            results["external_links"] = [self._see_more_link(query, zip_code)]
            return results
        except Exception as e:
            logger.warning(f"Row52 scrape failed: {e}")
            return self._generate_links(query, zip_code)

    async def _scrape(self, query: str, zip_code: str) -> Dict[str, Any]:
        """Fetch and parse Row52 search results."""
        encoded = quote_plus(query)
        params = f"YMMorVIN={encoded}"
        if zip_code:
            params += f"&ZipCode={zip_code}&Distance=50"

        url = f"https://row52.com/Search/?{params}"
        html, _ = await fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        salvage_hits = []

        # Row52 lists vehicles in card/list format
        cards = soup.select(".vehicle-card, .search-result, .result-item, .vehicle-listing")
        if not cards:
            # Fallback: look for common result containers
            cards = soup.select("[class*='result'], [class*='vehicle'], [class*='listing']")

        for card in cards:
            # Extract vehicle info (year make model)
            title_el = card.select_one(
                "h3, h4, .vehicle-title, .title, .vehicle-name, "
                "[class*='title'], [class*='vehicle'] a"
            )
            vehicle = title_el.get_text(strip=True) if title_el else ""

            # Extract yard name
            yard_el = card.select_one(
                ".yard-name, .location-name, [class*='yard'], [class*='location'] .name"
            )
            yard_name = yard_el.get_text(strip=True) if yard_el else ""

            # Extract yard location
            loc_el = card.select_one(
                ".yard-location, .location, .address, [class*='city'], [class*='address']"
            )
            yard_location = loc_el.get_text(strip=True) if loc_el else ""

            # Extract link
            link_tag = card.find("a", href=True)
            hit_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    hit_url = f"https://row52.com{href}"
                else:
                    hit_url = clean_url(href) if href else ""

            if vehicle:
                salvage_hits.append(SalvageHit(
                    source="row52",
                    yard_name=yard_name or "Unknown Yard",
                    yard_location=yard_location,
                    vehicle=vehicle,
                    url=hit_url or "https://row52.com",
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
        """Generate Row52 search links (fallback)."""
        encoded = quote_plus(query)
        params = f"YMMorVIN={encoded}"
        if zip_code:
            params += f"&ZipCode={zip_code}&Distance=50"

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": [
                ExternalLink(
                    label=f"Search Row52 for '{query}'",
                    url=f"https://row52.com/Search?{params}",
                    source="row52",
                    category="used_salvage",
                )
            ],
            "error": None,
        }

    def _see_more_link(self, query: str, zip_code: str) -> ExternalLink:
        """Single 'see more' link for Row52."""
        encoded = quote_plus(query)
        params = f"YMMorVIN={encoded}"
        if zip_code:
            params += f"&ZipCode={zip_code}&Distance=50"
        return ExternalLink(
            label="See all results on Row52",
            url=f"https://row52.com/Search?{params}",
            source="row52",
            category="used_salvage",
        )
