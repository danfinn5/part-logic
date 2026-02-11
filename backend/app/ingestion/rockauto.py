"""
RockAuto connector.

Uses Playwright to scrape JS-rendered search results from RockAuto.
Falls back to link generation when Playwright is unavailable or scraping fails.
"""
import logging
from typing import Dict, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from app.ingestion.base import BaseConnector
from app.schemas.search import MarketListing, ExternalLink
from app.config import settings
from app.utils.scraping import parse_price
from app.utils.normalization import clean_url
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
            # Wait for product listings to render
            try:
                await page.wait_for_selector(
                    "[class*='listing'], [class*='part'], .ra-listing-text, table.nobmar",
                    timeout=8000,
                )
            except Exception:
                pass  # Continue with whatever loaded

            html = await page.content()

        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # RockAuto uses table-based layouts with specific CSS classes
        parts = soup.select(
            "tr[class*='ra-listing'], .ra-listing-text, "
            "[class*='listing-text'], [class*='napa'], "
            "tr.ra-border-bottom, td.listing-text"
        )

        if not parts:
            # Broader fallback: look for any product-like rows
            parts = soup.select("tr")

        for part in parts:
            # Title / part description
            title_el = part.select_one(
                ".listing-text-row-title, .ra-listing-text, "
                "[class*='listing-text'], span.ra-listing-text, "
                "a[class*='listing']"
            )
            if not title_el:
                # Try text within td cells
                tds = part.find_all("td")
                title_text_parts = []
                for td in tds:
                    text = td.get_text(strip=True)
                    if text and len(text) > 5 and not text.startswith("$"):
                        title_text_parts.append(text)
                title = " ".join(title_text_parts[:2]) if title_text_parts else ""
            else:
                title = title_el.get_text(strip=True)

            # Price
            price_el = part.select_one(
                "[class*='price'], .ra-price, .listing-price, "
                "span.ra-price-display"
            )
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            # URL
            link_tag = part.select_one("a[href]")
            product_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    product_url = f"https://www.rockauto.com{href}"
                elif href.startswith("http"):
                    product_url = href

            # Image
            img_tag = part.select_one("img[src]")
            image_url = None
            if img_tag:
                src = img_tag.get("src", "")
                if src and not src.startswith("data:"):
                    if src.startswith("/"):
                        image_url = f"https://www.rockauto.com{src}"
                    elif src.startswith("http"):
                        image_url = src

            # Brand (often in a separate cell or span)
            brand_el = part.select_one(
                "[class*='brand'], .listing-brand, .ra-brand"
            )
            brand = brand_el.get_text(strip=True) if brand_el else None

            if not title or len(title) < 3:
                continue

            part_numbers = extract_part_numbers(title)

            listings.append(MarketListing(
                source="rockauto",
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
