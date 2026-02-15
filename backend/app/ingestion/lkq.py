"""
LKQ Online connector.

LKQ is a major recycled OEM parts network. Their website uses
a search interface at lkqonline.com.
Scrapes results when possible, falls back to link generation.
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


class LKQConnector(BaseConnector):
    """LKQ Online recycled OEM parts scraper with link fallback."""

    def __init__(self):
        super().__init__("lkq")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Search LKQ Online. Scrapes when enabled, falls back to links."""
        if not settings.scrape_enabled:
            return self._generate_links(query, kwargs)

        try:
            results = await self._scrape(query, **kwargs)
            if results["market_listings"] or results["salvage_hits"]:
                results["external_links"] = [self._see_more_link(query)]
                return results
            logger.info("LKQ scrape returned 0 results")
        except Exception as e:
            logger.warning(f"LKQ scrape failed: {e}")

        return self._generate_links(query, kwargs)

    async def _scrape(self, query: str, **kwargs) -> dict[str, Any]:
        """Fetch and parse LKQ Online search results."""
        encoded = quote_plus(query)
        url = f"https://www.lkqonline.com/search?q={encoded}"
        html, status = await fetch_html(url, retries=2)
        soup = BeautifulSoup(html, "html.parser")

        listings = []

        # LKQ product cards
        products = soup.select(".product-card, [class*='product'], .search-result, [class*='ProductCard']")

        for product in products:
            title_el = product.select_one(".product-title, h3 a, h2 a, [class*='title'] a, [class*='name']")
            title = title_el.get_text(strip=True) if title_el else ""

            price_el = product.select_one(".product-price, [class*='price']")
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            link_tag = product.select_one("a[href]")
            product_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    product_url = f"https://www.lkqonline.com{href}"
                elif href.startswith("http"):
                    product_url = href

            img_tag = product.select_one("img[src], img[data-src]")
            image_url = None
            if img_tag:
                src = img_tag.get("data-src") or img_tag.get("src", "")
                if src and src.startswith("http") and "data:" not in src:
                    image_url = src

            if not title:
                continue

            listings.append(
                MarketListing(
                    source="lkq",
                    title=title,
                    price=price,
                    condition="Used - Recycled OEM",
                    url=product_url or url,
                    part_numbers=extract_part_numbers(title),
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
        """Generate LKQ search links (fallback)."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search LKQ recycled parts for '{query}'",
                url=f"https://www.lkqonline.com/search?q={encoded}",
                source="lkq",
                category="used_parts",
            )
        ]
        for pn in (kwargs or {}).get("part_numbers", []):
            encoded_pn = quote_plus(pn)
            links.append(
                ExternalLink(
                    label=f"LKQ: {pn}",
                    url=f"https://www.lkqonline.com/search?q={encoded_pn}",
                    source="lkq",
                    category="used_parts",
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
            label="See all results on LKQ Online",
            url=f"https://www.lkqonline.com/search?q={encoded}",
            source="lkq",
            category="used_parts",
        )
