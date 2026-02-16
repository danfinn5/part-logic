"""
ECS Tuning connector.

Uses Playwright to bypass Cloudflare protection and scrape search results.
Falls back to link generation when Playwright is unavailable or scraping fails.
"""

import logging
from typing import Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.config import settings
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink, MarketListing
from app.utils.part_numbers import extract_part_numbers
from app.utils.scraping import parse_price

logger = logging.getLogger(__name__)


class ECSTuningConnector(BaseConnector):
    """ECS Tuning Playwright-based scraper (Cloudflare-protected site)."""

    def __init__(self):
        super().__init__("ecstuning")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Search ECS Tuning. Uses Playwright to bypass Cloudflare."""
        if not settings.scrape_enabled or not settings.playwright_enabled:
            return self._generate_links(query, kwargs)

        try:
            results = await self._scrape(query, **kwargs)
            results["external_links"] = [self._see_more_link(query)]
            return results
        except Exception as e:
            logger.warning(f"ECS Tuning scrape failed: {e}")
            return self._generate_links(query, kwargs)

    async def _scrape(self, query: str, **kwargs) -> dict[str, Any]:
        """Use Playwright to fetch and parse ECS Tuning search results."""
        from app.utils.browser import get_page

        encoded = quote_plus(query)
        url = f"https://www.ecstuning.com/Search/{encoded}/"

        async with get_page() as page:
            await page.goto(url, wait_until="networkidle")
            try:
                await page.wait_for_selector(
                    "[class*='product'], [class*='listing'], [data-product-id]",
                    timeout=10000,
                )
            except Exception:
                pass

            html = await page.content()

        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # Look for product cards
        products = soup.select(
            ".product-card, [data-product-id], [class*='product-card'], "
            ".product-item, [class*='productCard'], .grid-item"
        )

        for product in products:
            # Title
            title_el = product.select_one(".product-name, .product-title, h3, h4, [class*='title'], [class*='name'] a")
            title = title_el.get_text(strip=True) if title_el else ""

            # Price
            price_el = product.select_one(".price, .product-price, [class*='price'], .sale-price")
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            # URL
            link_tag = product.select_one("a[href]")
            product_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    product_url = f"https://www.ecstuning.com{href}"
                elif href.startswith("http"):
                    product_url = href

            # Image
            img_tag = product.select_one("img[src], img[data-src]")
            image_url = None
            if img_tag:
                image_url = img_tag.get("data-src") or img_tag.get("src", "")
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://www.ecstuning.com{image_url}"
                if image_url and image_url.startswith("data:"):
                    image_url = None

            # Brand
            brand_el = product.select_one(".brand, .manufacturer, [class*='brand']")
            brand = brand_el.get_text(strip=True) if brand_el else None

            # Part number
            pn_el = product.select_one(".part-number, .sku, [class*='partNumber'], [class*='sku']")
            part_num = pn_el.get_text(strip=True) if pn_el else ""

            if not title:
                continue

            part_numbers = [part_num] if part_num else extract_part_numbers(title)

            listings.append(
                MarketListing(
                    source="ecstuning",
                    title=title,
                    price=price,
                    condition="New",
                    url=product_url or url,
                    part_numbers=part_numbers,
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
        """Generate ECS Tuning search links (fallback)."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search ECS Tuning for '{query}'",
                url=f"https://www.ecstuning.com/Search/{encoded}/",
                source="ecstuning",
                category="new_parts",
            )
        ]

        part_numbers = (kwargs or {}).get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(
                ExternalLink(
                    label=f"ECS Tuning: {pn}",
                    url=f"https://www.ecstuning.com/Search/{encoded_pn}/",
                    source="ecstuning",
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
        """Single 'see more' link for ECS Tuning."""
        encoded = quote_plus(query)
        return ExternalLink(
            label="See all results on ECS Tuning",
            url=f"https://www.ecstuning.com/Search/{encoded}/",
            source="ecstuning",
            category="new_parts",
        )
