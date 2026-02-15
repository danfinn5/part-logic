"""
RockAuto connector.

Uses Playwright to scrape JS-rendered search results from RockAuto.
Falls back to link generation when Playwright is unavailable or scraping fails.
"""
import re
import logging
from typing import Dict, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from app.ingestion.base import BaseConnector
from app.schemas.search import MarketListing, ExternalLink
from app.config import settings
from app.utils.scraping import parse_price
from app.utils.part_numbers import extract_part_numbers

logger = logging.getLogger(__name__)


class RockAutoConnector(BaseConnector):
    """RockAuto Playwright-based scraper with link fallback."""

    def __init__(self):
        super().__init__("rockauto")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search RockAuto. Scrapes with Playwright when enabled, otherwise generates links."""
        if not settings.scrape_enabled or not settings.playwright_enabled:
            return self._generate_links(query, kwargs)

        try:
            results = await self._scrape(query, **kwargs)
            results["external_links"] = [self._see_more_link(query)]
            return results
        except Exception as e:
            logger.warning(f"RockAuto scrape failed: {e}")
            return self._generate_links(query, kwargs)

    async def _scrape(self, query: str, **kwargs) -> Dict[str, Any]:
        """Use Playwright to fetch and parse RockAuto search results."""
        from app.utils.browser import get_page

        encoded = quote_plus(query)
        url = f"https://www.rockauto.com/en/partsearch/?partnum={encoded}"

        async with get_page() as page:
            await page.goto(url, wait_until="networkidle")
            try:
                await page.wait_for_selector(
                    ".listing-inner, .listings-container",
                    timeout=8000,
                )
            except Exception:
                pass

            html = await page.content()

        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # RockAuto real structure: each part is a <tbody class="listing-inner">
        parts = soup.select("tbody.listing-inner")

        for part in parts:
            # Brand: <span class="listing-final-manufacturer">
            brand_el = part.select_one("span.listing-final-manufacturer")
            brand = brand_el.get_text(strip=True) if brand_el else None

            # Part number: <span class="listing-final-partnumber">
            pn_el = part.select_one("span.listing-final-partnumber")
            part_num = pn_el.get_text(strip=True) if pn_el else ""

            # Description text from listing-text-row-moreinfo or listing-text-row
            desc_el = part.select_one(".listing-text-row-moreinfo-truck, .listing-text-row-moreinfo")
            if desc_el:
                # Get just the direct text, not nested elements like "Info" button
                desc_parts = []
                if brand:
                    desc_parts.append(brand)
                if part_num:
                    desc_parts.append(part_num)
                # Get the description after manufacturer/partnumber
                footnote = part.select_one("span.listing-footnote-text")
                if footnote:
                    desc_parts.append(footnote.get_text(strip=True))
                title = " ".join(desc_parts) if desc_parts else ""
            else:
                title = f"{brand or ''} {part_num or ''}".strip()

            # Also grab the full text after brand+PN for more detail
            more_el = part.select_one(".listing-text-row-moreinfo-truck")
            if more_el and not title:
                raw = more_el.get_text(strip=True)
                # Remove "Info" button text
                title = raw.replace("Info", "").strip()

            # Price: <span class="listing-price listing-amount-bold">
            price_el = part.select_one("span.listing-price")
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            # Image
            img_el = part.select_one(".listing-inline-image-popup-widget-title")
            image_url = None
            img_tag = part.select_one("img[src]")
            if img_tag:
                src = img_tag.get("src", "")
                if src and src.startswith("http") and not src.startswith("data:"):
                    image_url = src

            # Skip rows without meaningful content
            if not title or len(title) < 3:
                continue
            if not part_num and not brand:
                continue

            part_numbers = [part_num] if part_num else extract_part_numbers(title)

            listings.append(MarketListing(
                source="rockauto",
                title=title,
                price=price,
                condition="New",
                url=url,
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
        """Generate RockAuto search links (fallback)."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search RockAuto for '{query}'",
                url=f"https://www.rockauto.com/en/partsearch/?partnum={encoded}",
                source="rockauto",
                category="new_parts",
            )
        ]

        part_numbers = (kwargs or {}).get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"RockAuto: {pn}",
                url=f"https://www.rockauto.com/en/partsearch/?partnum={encoded_pn}",
                source="rockauto",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }

    def _see_more_link(self, query: str) -> ExternalLink:
        """Single 'see more' link for RockAuto."""
        encoded = quote_plus(query)
        return ExternalLink(
            label="See all results on RockAuto",
            url=f"https://www.rockauto.com/en/partsearch/?partnum={encoded}",
            source="rockauto",
            category="new_parts",
        )
