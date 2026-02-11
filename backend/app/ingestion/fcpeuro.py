"""
FCP Euro connector.

Tries FCP Euro's internal search API first, then falls back to
HTML scraping, then to link generation.
"""
import logging
from typing import Dict, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from app.ingestion.base import BaseConnector
from app.schemas.search import MarketListing, ExternalLink
from app.config import settings
from app.utils.scraping import fetch_html, fetch_json, parse_price
from app.utils.normalization import clean_url
from app.utils.part_numbers import extract_part_numbers

logger = logging.getLogger(__name__)


class FCPEuroConnector(BaseConnector):
    """FCP Euro scraper for European car parts with lifetime guarantee."""

    def __init__(self):
        super().__init__("fcpeuro")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search FCP Euro. Scrapes real results, falls back to links."""
        if not settings.scrape_enabled:
            return self._generate_links(query, kwargs)

        try:
            results = await self._scrape(query, **kwargs)
            results["external_links"] = [self._see_more_link(query)]
            return results
        except Exception as e:
            logger.warning(f"FCP Euro scrape failed: {e}")
            return self._generate_links(query, kwargs)

    async def _scrape(self, query: str, **kwargs) -> Dict[str, Any]:
        """Try API first, then HTML parsing."""
        try:
            return await self._scrape_api(query)
        except Exception as e:
            logger.debug(f"FCP Euro API attempt failed: {e}, trying HTML")

        return await self._scrape_html(query)

    async def _scrape_api(self, query: str) -> Dict[str, Any]:
        """Try FCP Euro's internal search API."""
        encoded = quote_plus(query)
        api_url = f"https://www.fcpeuro.com/api/search?query={encoded}"
        data, _ = await fetch_json(api_url, headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.fcpeuro.com/",
        })

        listings = []
        products = data.get("products", data.get("items", data.get("results", [])))
        for product in products:
            title = product.get("name", product.get("title", ""))
            price = parse_price(str(product.get("price", product.get("salePrice", "0"))))
            url = product.get("url", product.get("link", ""))
            image = product.get("image", product.get("imageUrl", product.get("thumbnail", "")))
            brand = product.get("brand", product.get("manufacturer", ""))
            part_num = product.get("partNumber", product.get("sku", ""))

            if not title:
                continue

            part_numbers = [part_num] if part_num else extract_part_numbers(title)

            if url and not url.startswith("http"):
                url = f"https://www.fcpeuro.com{url}"

            listings.append(MarketListing(
                source="fcpeuro",
                title=title,
                price=price,
                condition="New",
                url=clean_url(url) if url else f"https://www.fcpeuro.com/search?query={encoded}",
                part_numbers=part_numbers,
                brand=brand or None,
                image_url=clean_url(image) if image else None,
            ))

            if len(listings) >= settings.max_results_per_source:
                break

        return {
            "market_listings": listings,
            "salvage_hits": [],
            "external_links": [],
            "error": None,
        }

    async def _scrape_html(self, query: str) -> Dict[str, Any]:
        """Parse FCP Euro HTML search results."""
        encoded = quote_plus(query)
        url = f"https://www.fcpeuro.com/search?query={encoded}"
        html, _ = await fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        listings = []

        products = soup.select(
            ".product-card, .search-result, .product-item, "
            "[class*='product-card'], [class*='productCard'], "
            "[data-product-id], .grid-item"
        )

        for product in products:
            # Title
            title_el = product.select_one(
                ".product-name, .product-title, h3, h4, "
                "[class*='title'], [class*='name'] a"
            )
            title = title_el.get_text(strip=True) if title_el else ""

            # Price
            price_el = product.select_one(
                ".price, .product-price, [class*='price'], .sale-price"
            )
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            # URL
            link_tag = product.select_one("a[href]")
            product_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    product_url = f"https://www.fcpeuro.com{href}"
                else:
                    product_url = clean_url(href)

            # Image
            img_tag = product.select_one("img[src], img[data-src]")
            image_url = None
            if img_tag:
                image_url = img_tag.get("data-src") or img_tag.get("src", "")
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://www.fcpeuro.com{image_url}"

            # Brand
            brand_el = product.select_one(".brand, .manufacturer, [class*='brand']")
            brand = brand_el.get_text(strip=True) if brand_el else None

            # Part number
            pn_el = product.select_one(".part-number, .sku, [class*='partNumber'], [class*='sku']")
            part_num = pn_el.get_text(strip=True) if pn_el else ""

            if not title:
                continue

            part_numbers = [part_num] if part_num else extract_part_numbers(title)

            listings.append(MarketListing(
                source="fcpeuro",
                title=title,
                price=price,
                condition="New",
                url=product_url or url,
                part_numbers=part_numbers,
                brand=brand,
                image_url=image_url,
            ))

            if len(listings) >= settings.max_results_per_source:
                break

        return {
            "market_listings": listings,
            "salvage_hits": [],
            "external_links": [],
            "error": None,
        }

    def _generate_links(self, query: str, kwargs: dict = None) -> Dict[str, Any]:
        """Generate FCP Euro search links (fallback)."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search FCP Euro for '{query}'",
                url=f"https://www.fcpeuro.com/search?query={encoded}",
                source="fcpeuro",
                category="new_parts",
            )
        ]

        part_numbers = (kwargs or {}).get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"FCP Euro: {pn}",
                url=f"https://www.fcpeuro.com/search?query={encoded_pn}",
                source="fcpeuro",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }

    def _see_more_link(self, query: str) -> ExternalLink:
        """Single 'see more' link for FCP Euro."""
        encoded = quote_plus(query)
        return ExternalLink(
            label="See all results on FCP Euro",
            url=f"https://www.fcpeuro.com/search?query={encoded}",
            source="fcpeuro",
            category="new_parts",
        )
