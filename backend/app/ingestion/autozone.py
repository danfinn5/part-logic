"""
AutoZone connector.

Scrapes AutoZone search results using server-rendered HTML.
AutoZone's search pages are reasonably well-structured with
product cards containing price, brand, part number, and fitment data.
Falls back to link generation on failure.
"""

import logging
from typing import Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.config import settings
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink, MarketListing
from app.utils.part_numbers import extract_part_numbers
from app.utils.scraping import fetch_html, parse_price

logger = logging.getLogger(__name__)


class AutoZoneConnector(BaseConnector):
    """AutoZone scraper with link fallback."""

    def __init__(self):
        super().__init__("autozone")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Search AutoZone. Scrapes when enabled, falls back to links."""
        if not settings.scrape_enabled:
            return self._generate_links(query, kwargs)

        try:
            results = await self._scrape(query, **kwargs)
            if results["market_listings"]:
                results["external_links"] = [self._see_more_link(query)]
                return results
            logger.info("AutoZone scrape returned 0 listings")
        except Exception as e:
            logger.warning(f"AutoZone scrape failed: {e}")

        return self._generate_links(query, kwargs)

    async def _scrape(self, query: str, **kwargs) -> dict[str, Any]:
        """Fetch and parse AutoZone search results."""
        encoded = quote_plus(query)
        url = f"https://www.autozone.com/searchresult?searchText={encoded}"
        html, status = await fetch_html(url, retries=2)
        soup = BeautifulSoup(html, "html.parser")

        listings = []

        # AutoZone product cards
        products = soup.select(
            "[data-testid='product-card'], .product-card, [class*='ProductCard'], [class*='product-listing']"
        )

        for product in products:
            # Title
            title_el = product.select_one(
                "[data-testid='product-title'], .product-title, h3 a, h2 a, [class*='title'] a"
            )
            title = title_el.get_text(strip=True) if title_el else ""

            # Price
            price_el = product.select_one(
                "[data-testid='product-price'], .product-price, [class*='price'], .sale-price"
            )
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            # URL
            link_tag = product.select_one("a[href]")
            product_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    product_url = f"https://www.autozone.com{href}"
                elif href.startswith("http"):
                    product_url = href

            # Image
            img_tag = product.select_one("img[src], img[data-src]")
            image_url = None
            if img_tag:
                src = img_tag.get("data-src") or img_tag.get("src", "")
                if src and src.startswith("http") and "data:" not in src:
                    image_url = src

            # Brand
            brand_el = product.select_one("[class*='brand'], .brand-name")
            brand = brand_el.get_text(strip=True) if brand_el else None

            if not title:
                continue

            listings.append(
                MarketListing(
                    source="autozone",
                    title=title,
                    price=price,
                    condition="New",
                    url=product_url or url,
                    part_numbers=extract_part_numbers(title),
                    brand=brand,
                    image_url=image_url,
                )
            )

            if len(listings) >= settings.max_results_per_source:
                break

        return {
            "market_listings": listings,
            "salvage_hits": [],
            "external_links": [],
            "error": None,
        }

    def _generate_links(self, query: str, kwargs: dict = None) -> dict[str, Any]:
        """Generate AutoZone search links (fallback)."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search AutoZone for '{query}'",
                url=f"https://www.autozone.com/searchresult?searchText={encoded}",
                source="autozone",
                category="new_parts",
            )
        ]
        for pn in (kwargs or {}).get("part_numbers", []):
            encoded_pn = quote_plus(pn)
            links.append(
                ExternalLink(
                    label=f"AutoZone: {pn}",
                    url=f"https://www.autozone.com/searchresult?searchText={encoded_pn}",
                    source="autozone",
                    category="new_parts",
                )
            )
        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }

    def _see_more_link(self, query: str) -> ExternalLink:
        encoded = quote_plus(query)
        return ExternalLink(
            label="See all results on AutoZone",
            url=f"https://www.autozone.com/searchresult?searchText={encoded}",
            source="autozone",
            category="new_parts",
        )
