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

        # Row52 real structure: each vehicle is a <div class="list-row">
        # with schema.org itemprop attributes for year, make, model, vin
        rows = soup.select("div.list-row")

        for row in rows:
            # Year/Make/Model from schema.org meta tags
            year_meta = row.select_one('meta[itemprop="year"]')
            make_meta = row.select_one('meta[itemprop="make"]')
            model_meta = row.select_one('meta[itemprop="model"]')

            year = year_meta.get("content", "") if year_meta else ""
            make = make_meta.get("content", "") if make_meta else ""
            model = model_meta.get("content", "") if model_meta else ""

            vehicle = f"{year} {make} {model}".strip()
            if not vehicle or vehicle == "":
                continue

            # Yard info from schema.org AutomotiveBusiness
            yard_name_el = row.select_one(
                '[itemtype*="AutomotiveBusiness"] span[itemprop="name"] strong, '
                '[itemtype*="AutomotiveBusiness"] span[itemprop="name"]'
            )
            yard_name = yard_name_el.get_text(strip=True) if yard_name_el else "Unknown Yard"

            # Yard location
            yard_loc_el = row.select_one('p[itemprop="address"]')
            yard_location = yard_loc_el.get_text(strip=True) if yard_loc_el else ""

            # Vehicle detail URL
            link_tag = row.select_one('a[itemprop="url"]')
            hit_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    hit_url = f"https://row52.com{href}"

            # Date added
            date_el = row.select_one('.col-md-1 strong')
            last_seen = None
            # Look for date in the row's text
            date_cells = row.select('.col-md-1')
            for cell in date_cells:
                strong = cell.select_one('strong')
                if strong:
                    text = strong.get_text(strip=True)
                    if ',' in text and any(m in text for m in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                        last_seen = text
                        break

            salvage_hits.append(SalvageHit(
                source="row52",
                yard_name=yard_name,
                yard_location=yard_location,
                vehicle=vehicle,
                url=hit_url or "https://row52.com",
                last_seen=last_seen,
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
