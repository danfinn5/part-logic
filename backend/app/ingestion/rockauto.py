"""
RockAuto connector using web scraping.
Minimal but working implementation with rate limiting and error handling.
"""
import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import Dict, Any, List, Optional
from app.ingestion.base import BaseConnector
from app.schemas.search import MarketListing
from app.config import settings
from app.utils.normalization import normalize_price, clean_url
from app.utils.part_numbers import extract_part_numbers
import logging

logger = logging.getLogger(__name__)


class RockAutoConnector(BaseConnector):
    """RockAuto web scraper connector."""
    
    def __init__(self):
        super().__init__("rockauto")
        self.base_url = "https://www.rockauto.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    async def search(self, query: str, max_results: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Search RockAuto by part number/keywords.
        Note: RockAuto doesn't have a simple search endpoint, so we'll search via their catalog.
        """
        try:
            # Rate limit
            await asyncio.sleep(settings.rate_limit_delay)
            
            # RockAuto search URL
            # They use a complex catalog system, so we'll try a direct part number search
            search_url = f"{self.base_url}/en/catalog"
            
            # RockAuto uses POST for searches, but we'll try GET with query params first
            params = {
                "keywords": query,
            }
            
            async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
                response = await client.get(
                    search_url,
                    params=params,
                    headers=self.headers
                )
                
                # If we get redirected or get a catalog page, try to parse it
                if response.status_code == 200:
                    listings = self._parse_search_results(response.text, query)
                    return {
                        "market_listings": listings[:max_results],
                        "salvage_hits": [],
                        "external_links": [],
                        "error": None
                    }
                else:
                    # RockAuto might require more complex navigation
                    # Return empty with a note that this needs more work
                    logger.warning(f"RockAuto returned status {response.status_code}")
                    return {
                        "market_listings": [],
                        "salvage_hits": [],
                        "external_links": [],
                        "error": f"RockAuto search returned status {response.status_code}. TODO: Implement full catalog navigation."
                    }
        
        except httpx.TimeoutException:
            logger.error("RockAuto request timeout")
            return {
                "market_listings": [],
                "salvage_hits": [],
                "external_links": [],
                "error": "Request timeout"
            }
        except Exception as e:
            logger.error(f"RockAuto search error: {e}")
            return {
                "market_listings": [],
                "salvage_hits": [],
                "external_links": [],
                "error": str(e)
            }
    
    def _parse_search_results(self, html: str, query: str) -> List[MarketListing]:
        """
        Parse RockAuto search results HTML.
        This is a minimal implementation - RockAuto's structure may vary.
        """
        listings = []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # RockAuto product listings are typically in specific divs/classes
            # This is a best-effort parser - structure may need adjustment
            product_divs = soup.find_all("div", class_=lambda x: x and ("product" in x.lower() or "listing" in x.lower()))
            
            if not product_divs:
                # Try alternative selectors
                product_divs = soup.find_all("tr", class_=lambda x: x and "listing" in x.lower())
            
            for div in product_divs[:settings.max_results_per_source]:
                try:
                    # Extract title/link
                    title_elem = div.find("a") or div.find("span", class_=lambda x: x and "title" in x.lower())
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")
                    if link and not link.startswith("http"):
                        link = f"{self.base_url}{link}"
                    
                    # Extract price
                    price_elem = div.find("span", class_=lambda x: x and "price" in x.lower()) or \
                                div.find("div", class_=lambda x: x and "price" in x.lower())
                    price_str = price_elem.get_text(strip=True) if price_elem else "0"
                    
                    # Extract part number if available
                    part_num_elem = div.find("span", class_=lambda x: x and "part" in x.lower() and "number" in x.lower())
                    part_numbers = extract_part_numbers(title)
                    if part_num_elem:
                        part_num_text = part_num_elem.get_text(strip=True)
                        part_numbers.extend(extract_part_numbers(part_num_text))
                    
                    listing = MarketListing(
                        source="rockauto",
                        title=title,
                        price=normalize_price(price_str),
                        currency="USD",
                        condition="New",  # RockAuto typically sells new parts
                        url=clean_url(link),
                        part_numbers=list(set(part_numbers)),  # Deduplicate
                        vendor="RockAuto"
                    )
                    listings.append(listing)
                
                except Exception as e:
                    logger.warning(f"Error parsing RockAuto listing: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing RockAuto HTML: {e}")
        
        # If we didn't find anything with the standard parser, return empty
        # This indicates the page structure is different than expected
        return listings
