"""
Row52 connector for salvage yard inventory searches.
Minimal but working implementation.
"""
import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import Dict, Any, List, Optional
from app.ingestion.base import BaseConnector
from app.schemas.search import SalvageHit
from app.config import settings
from app.utils.normalization import clean_url
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Row52Connector(BaseConnector):
    """Row52 salvage yard inventory connector."""
    
    def __init__(self):
        super().__init__("row52")
        self.base_url = "https://row52.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    async def search(self, query: str, max_results: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Search Row52 for salvage yard inventory.
        """
        try:
            # Rate limit
            await asyncio.sleep(settings.rate_limit_delay)
            
            # Row52 search URL
            # They have a search endpoint that accepts queries
            search_url = f"{self.base_url}/Search"
            
            params = {
                "Query": query,
            }
            
            async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
                response = await client.get(
                    search_url,
                    params=params,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    hits = self._parse_search_results(response.text, query)
                    return {
                        "market_listings": [],
                        "salvage_hits": hits[:max_results],
                        "external_links": [],
                        "error": None
                    }
                else:
                    logger.warning(f"Row52 returned status {response.status_code}")
                    return {
                        "market_listings": [],
                        "salvage_hits": [],
                        "external_links": [],
                        "error": f"Row52 search returned status {response.status_code}"
                    }
        
        except httpx.TimeoutException:
            logger.error("Row52 request timeout")
            return {
                "market_listings": [],
                "salvage_hits": [],
                "external_links": [],
                "error": "Request timeout"
            }
        except Exception as e:
            logger.error(f"Row52 search error: {e}")
            return {
                "market_listings": [],
                "salvage_hits": [],
                "external_links": [],
                "error": str(e)
            }
    
    def _parse_search_results(self, html: str, query: str) -> List[SalvageHit]:
        """
        Parse Row52 search results HTML.
        Best-effort implementation - structure may need adjustment.
        """
        hits = []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Row52 typically shows results in table rows or divs with vehicle/yard info
            # Look for common patterns
            result_rows = soup.find_all("tr", class_=lambda x: x and ("vehicle" in x.lower() or "listing" in x.lower()))
            
            if not result_rows:
                # Try div-based layout
                result_rows = soup.find_all("div", class_=lambda x: x and ("vehicle" in x.lower() or "listing" in x.lower() or "result" in x.lower()))
            
            for row in result_rows[:settings.max_results_per_source]:
                try:
                    # Extract yard name
                    yard_elem = row.find("a", class_=lambda x: x and "yard" in x.lower()) or \
                               row.find("span", class_=lambda x: x and "yard" in x.lower())
                    yard_name = yard_elem.get_text(strip=True) if yard_elem else "Unknown Yard"
                    
                    # Extract yard location
                    location_elem = row.find("span", class_=lambda x: x and ("location" in x.lower() or "city" in x.lower()))
                    yard_location = location_elem.get_text(strip=True) if location_elem else "Unknown"
                    
                    # Extract vehicle info
                    vehicle_elem = row.find("a", class_=lambda x: x and "vehicle" in x.lower()) or \
                                  row.find("span", class_=lambda x: x and "vehicle" in x.lower())
                    vehicle = vehicle_elem.get_text(strip=True) if vehicle_elem else query
                    
                    # Extract URL
                    link_elem = row.find("a", href=True)
                    url = link_elem.get("href", "") if link_elem else ""
                    if url and not url.startswith("http"):
                        url = f"{self.base_url}{url}"
                    
                    # Extract part description if available
                    part_desc_elem = row.find("span", class_=lambda x: x and "part" in x.lower())
                    part_description = part_desc_elem.get_text(strip=True) if part_desc_elem else None
                    
                    hit = SalvageHit(
                        source="row52",
                        yard_name=yard_name,
                        yard_location=yard_location,
                        vehicle=vehicle,
                        url=clean_url(url),
                        last_seen=datetime.now().strftime("%Y-%m-%d"),
                        part_description=part_description
                    )
                    hits.append(hit)
                
                except Exception as e:
                    logger.warning(f"Error parsing Row52 result: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing Row52 HTML: {e}")
        
        return hits
