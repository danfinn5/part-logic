"""
Partsouq OEM parts connector.

Uses Playwright to bypass Cloudflare protection and scrape OEM part listings.
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


class PartsouqConnector(BaseConnector):
    """Partsouq OEM parts Playwright-based scraper (Cloudflare-protected)."""

    def __init__(self):
        super().__init__("partsouq")

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search Partsouq. Uses Playwright to bypass Cloudflare."""
        if not settings.scrape_enabled or not settings.playwright_enabled:
            return self._generate_links(query, kwargs)

        try:
            results = await self._scrape(query, **kwargs)
            results["external_links"] = [self._see_more_link(query)]
            return results
        except Exception as e:
            logger.warning(f"Partsouq scrape failed: {e}")
            return self._generate_links(query, kwargs)

    async def _scrape(self, query: str, **kwargs) -> Dict[str, Any]:
        """Use Playwright to fetch and parse Partsouq search results."""
        from app.utils.browser import get_page

        encoded = quote_plus(query)
        url = f"https://partsouq.com/en/search/all?q={encoded}"

        async with get_page() as page:
            await page.goto(url, wait_until="networkidle")
            try:
                await page.wait_for_selector(
                    "[class*='part'], [class*='product'], [class*='search-result']",
                    timeout=10000,
                )
            except Exception:
                pass

            html = await page.content()

        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # Look for part items
        products = soup.select(
            ".part-item, .search-result-item, .product-item, "
            "[class*='part-item'], [class*='search-result'], "
            "[class*='product'], .result-row"
        )

        for product in products:
            # Title / part name
            title_el = product.select_one(
                ".part-name, .product-name, .title, h3, h4, "
                "[class*='name'], [class*='title'] a"
            )
            title = title_el.get_text(strip=True) if title_el else ""

            # OEM part number
            pn_el = product.select_one(
                ".part-number, .oem-number, [class*='partNumber'], "
                "[class*='part-num'], [class*='oem'], .sku"
            )
            part_num = pn_el.get_text(strip=True) if pn_el else ""

            # Price
            price_el = product.select_one(
                ".price, .product-price, [class*='price']"
            )
            price = parse_price(price_el.get_text(strip=True)) if price_el else 0.0

            # URL
            link_tag = product.select_one("a[href]")
            product_url = ""
            if link_tag:
                href = link_tag.get("href", "")
                if href.startswith("/"):
                    product_url = f"https://partsouq.com{href}"
                elif href.startswith("http"):
                    product_url = href

            # Image
            img_tag = product.select_one("img[src], img[data-src]")
            image_url = None
            if img_tag:
                image_url = img_tag.get("data-src") or img_tag.get("src", "")
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://partsouq.com{image_url}"
                if image_url and image_url.startswith("data:"):
                    image_url = None

            if not title and not part_num:
                continue

            part_numbers = [part_num] if part_num else extract_part_numbers(title)

            listings.append(MarketListing(
                source="partsouq",
                title=title or f"OEM Part {part_num}",
                price=price,
                condition="New",
                url=product_url or url,
                part_numbers=part_numbers,
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
        """Generate Partsouq search links (fallback)."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"OEM diagrams on Partsouq for '{query}'",
                url=f"https://partsouq.com/en/search/all?q={encoded}",
                source="partsouq",
                category="new_parts",
            )
        ]

        part_numbers = (kwargs or {}).get("part_numbers") or extract_part_numbers(query)
        for pn in part_numbers:
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"Partsouq OEM: {pn}",
                url=f"https://partsouq.com/en/search/all?q={encoded_pn}",
                source="partsouq",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }

    def _see_more_link(self, query: str) -> ExternalLink:
        """Single 'see more' link for Partsouq."""
        encoded = quote_plus(query)
        return ExternalLink(
            label="See all results on Partsouq",
            url=f"https://partsouq.com/en/search/all?q={encoded}",
            source="partsouq",
            category="new_parts",
        )
