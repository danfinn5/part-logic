"""
FCP Euro connector.

Parses FCP Euro search results from server-rendered HTML.
FCP Euro embeds structured product data in GTM event attributes
and uses .hit cards for product display.

This is one of the most reliable scrapers — no JS rendering needed,
structured data available, and no aggressive bot blocking.
Falls back to link generation on failure.
"""

import json
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


class FCPEuroConnector(BaseConnector):
    """FCP Euro scraper for European car parts with lifetime guarantee."""

    def __init__(self):
        super().__init__("fcpeuro")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Search FCP Euro. Scrapes real results, falls back to links."""
        if not settings.scrape_enabled:
            return self._generate_links(query, kwargs)

        try:
            results = await self._scrape(query, **kwargs)
            if results["market_listings"]:
                results["external_links"] = [self._see_more_link(query)]
                return results
            # No results from scrape — fall through to links
            logger.info("FCP Euro scrape returned 0 listings, generating links instead")
        except Exception as e:
            logger.warning(f"FCP Euro scrape failed: {e}")

        return self._generate_links(query, kwargs)

    async def _scrape(self, query: str, **kwargs) -> dict[str, Any]:
        """Fetch and parse FCP Euro search results."""
        encoded = quote_plus(query)
        url = f"https://www.fcpeuro.com/products?keywords={encoded}"
        html, status = await fetch_html(url, retries=2)
        soup = BeautifulSoup(html, "html.parser")

        # Strategy 1: Extract from GTM JSON embedded in turbo-frame
        listings = self._parse_gtm_data(soup, query)
        if listings:
            # Enrich with image URLs and per-product links from HTML cards
            self._enrich_with_html(soup, listings)
            return {
                "market_listings": listings[: settings.max_results_per_source],
                "salvage_hits": [],
                "external_links": [],
                "error": None,
            }

        # Strategy 2: Parse HTML .hit cards directly
        listings = self._parse_hit_cards(soup, query)
        return {
            "market_listings": listings[: settings.max_results_per_source],
            "salvage_hits": [],
            "external_links": [],
            "error": None,
        }

    def _parse_gtm_data(self, soup: BeautifulSoup, query: str) -> list:
        """Extract product data from GTM event JSON in turbo-frame."""
        listings = []
        frame = soup.select_one("turbo-frame#product-results")
        if not frame:
            return listings

        gtm_raw = frame.get("data-gtm-event-event-value", "")
        if not gtm_raw:
            return listings

        try:
            data = json.loads(gtm_raw)
        except (json.JSONDecodeError, TypeError):
            return listings

        items = data.get("ecommerce", {}).get("items", [])
        for item in items:
            item_id = item.get("item_id", "")
            title = item.get("item_name", "")
            brand = item.get("item_brand", "")
            price = float(item.get("price", "0") or "0")

            if not title:
                continue

            part_numbers = extract_part_numbers(title)
            if item_id and item_id not in part_numbers:
                part_numbers.append(item_id)

            listings.append(
                MarketListing(
                    source="fcpeuro",
                    title=title,
                    price=price,
                    condition="New",
                    url=f"https://www.fcpeuro.com/products?keywords={quote_plus(query)}",
                    part_numbers=part_numbers,
                    brand=brand or None,
                )
            )

        return listings

    def _enrich_with_html(self, soup: BeautifulSoup, listings: list):
        """Add image URLs and product links from HTML .hit cards."""
        hits = soup.select("div.hit, .grid-x.hit")
        for i, hit in enumerate(hits):
            if i >= len(listings):
                break

            # Image
            img_tag = hit.select_one("img[src]")
            if img_tag:
                src = img_tag.get("src", "")
                if src and src.startswith("http"):
                    listings[i].image_url = src

            # Product URL
            link_tag = hit.select_one("a.hit__name[href]")
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    listings[i].url = f"https://www.fcpeuro.com{href}"

    def _parse_hit_cards(self, soup: BeautifulSoup, query: str) -> list:
        """Parse FCP Euro .hit cards when GTM data unavailable."""
        listings = []
        hits = soup.select("div.hit, .grid-x.hit")

        for hit in hits:
            # Title
            name_el = hit.select_one(".hit__name")
            title = name_el.get_text(strip=True) if name_el else ""

            # Price: in .hit__money
            price_el = hit.select_one(".hit__money")
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            # URL
            link_tag = hit.select_one("a.hit__name[href], a[href]")
            product_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    product_url = f"https://www.fcpeuro.com{href}"

            # Image
            img_tag = hit.select_one("img[src]")
            image_url = None
            if img_tag:
                src = img_tag.get("src", "")
                if src and src.startswith("http"):
                    image_url = src

            # Brand from .hit__flag (e.g., "OE")
            flag_el = hit.select_one(".hit__flag")
            brand = flag_el.get_text(strip=True) if flag_el else None

            if not title:
                continue

            listings.append(
                MarketListing(
                    source="fcpeuro",
                    title=title,
                    price=price,
                    condition="New",
                    url=product_url or f"https://www.fcpeuro.com/products?keywords={quote_plus(query)}",
                    part_numbers=extract_part_numbers(title),
                    brand=brand,
                    image_url=image_url,
                )
            )

        return listings

    def _generate_links(self, query: str, kwargs: dict = None) -> dict[str, Any]:
        """Generate FCP Euro search links (fallback)."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search FCP Euro for '{query}'",
                url=f"https://www.fcpeuro.com/products?keywords={encoded}",
                source="fcpeuro",
                category="new_parts",
            )
        ]

        part_numbers = (kwargs or {}).get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(
                ExternalLink(
                    label=f"FCP Euro: {pn}",
                    url=f"https://www.fcpeuro.com/products?keywords={encoded_pn}",
                    source="fcpeuro",
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
        """Single 'see more' link for FCP Euro."""
        encoded = quote_plus(query)
        return ExternalLink(
            label="See all results on FCP Euro",
            url=f"https://www.fcpeuro.com/products?keywords={encoded}",
            source="fcpeuro",
            category="new_parts",
        )
