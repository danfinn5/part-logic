"""
Amazon Automotive connector.

Uses Playwright to scrape JS-rendered search results from Amazon.
Falls back to link generation when Playwright is unavailable or scraping fails.
Amazon has strong anti-bot protections, so fallback is expected to be common.
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


class AmazonConnector(BaseConnector):
    """Amazon Automotive Playwright-based scraper with link fallback."""

    def __init__(self):
        super().__init__("amazon")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Search Amazon Automotive. Scrapes with Playwright, falls back to links."""
        if not settings.scrape_enabled or not settings.playwright_enabled:
            return self._generate_links(query, kwargs)

        try:
            results = await self._scrape(query, **kwargs)
            results["external_links"] = [self._see_more_link(query)]
            return results
        except Exception as e:
            logger.warning(f"Amazon scrape failed: {e}")
            return self._generate_links(query, kwargs)

    async def _scrape(self, query: str, **kwargs) -> dict[str, Any]:
        """Use Playwright to fetch and parse Amazon search results."""
        from app.utils.browser import get_page

        encoded = quote_plus(query)
        url = f"https://www.amazon.com/s?k={encoded}&i=automotive-intl-ship"

        async with get_page() as page:
            await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector(
                    "[data-component-type='s-search-result'], .s-result-item",
                    timeout=8000,
                )
            except Exception:
                pass

            html = await page.content()

        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # Amazon search results
        products = soup.select("[data-component-type='s-search-result'], .s-result-item[data-asin]")

        for product in products:
            asin = product.get("data-asin", "")
            if not asin:
                continue

            # Title
            title_el = product.select_one(
                "h2 a span, h2 span.a-text-normal, "
                ".a-size-medium.a-color-base.a-text-normal, "
                ".a-size-base-plus.a-color-base.a-text-normal"
            )
            title = title_el.get_text(strip=True) if title_el else ""

            # Price
            price_el = product.select_one(".a-price .a-offscreen, .a-price-whole, span.a-price span.a-offscreen")
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            # URL
            link_tag = product.select_one("h2 a[href]")
            product_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    product_url = f"https://www.amazon.com{href}"
                elif href.startswith("http"):
                    product_url = href

            # Image
            img_tag = product.select_one("img.s-image")
            image_url = img_tag.get("src") if img_tag else None

            # Rating
            rating_el = product.select_one("span.a-icon-alt")
            rating_text = rating_el.get_text(strip=True) if rating_el else None

            if not title:
                continue

            listings.append(
                MarketListing(
                    source="amazon",
                    title=title,
                    price=price,
                    condition="New",
                    url=product_url or f"https://www.amazon.com/dp/{asin}",
                    part_numbers=extract_part_numbers(title),
                    image_url=image_url,
                    vendor=rating_text,  # Store rating in vendor field as extra info
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
        """Generate Amazon Automotive search links (fallback)."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search Amazon Automotive for '{query}'",
                url=f"https://www.amazon.com/s?k={encoded}&i=automotive-intl-ship",
                source="amazon",
                category="new_parts",
            )
        ]

        part_numbers = (kwargs or {}).get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(
                ExternalLink(
                    label=f"Amazon: {pn}",
                    url=f"https://www.amazon.com/s?k={encoded_pn}&i=automotive-intl-ship",
                    source="amazon",
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
        """Single 'see more' link for Amazon."""
        encoded = quote_plus(query)
        return ExternalLink(
            label="See all results on Amazon",
            url=f"https://www.amazon.com/s?k={encoded}&i=automotive-intl-ship",
            source="amazon",
            category="new_parts",
        )
