"""
eBay Browse API connector for part searches.
Uses eBay Browse API (simpler than Finding API for basic searches).
"""
import httpx
from typing import Dict, Any, List, Optional
from app.ingestion.base import BaseConnector
from app.schemas.search import MarketListing
from app.config import settings
from app.utils.normalization import normalize_price, normalize_condition, clean_url
from app.utils.part_numbers import extract_part_numbers
import logging

logger = logging.getLogger(__name__)


class eBayConnector(BaseConnector):
    """eBay Browse API connector."""
    
    def __init__(self):
        super().__init__("ebay")
        self.app_id = settings.ebay_app_id
        self.base_url = "https://api.ebay.com" if not settings.ebay_sandbox else "https://api.sandbox.ebay.com"
    
    async def search(self, query: str, max_results: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Search eBay using Browse API.
        """
        if not self.app_id:
            return {
                "market_listings": [],
                "salvage_hits": [],
                "external_links": [],
                "error": "eBay App ID not configured"
            }
        
        try:
            # eBay Browse API endpoint
            url = f"{self.base_url}/buy/browse/v1/item_summary/search"
            
            params = {
                "q": query,
                "limit": min(max_results, settings.max_results_per_source),
            }
            
            headers = {
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=<ePNCampaignId>,affiliateReferenceId=<referenceId>",
            }
            
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                # eBay Browse API uses OAuth, but for simplicity we'll use the app_id in headers
                # Note: In production, you'd want to use OAuth 2.0 token
                headers["X-EBAY-SOA-SECURITY-APPNAME"] = self.app_id
                response = await client.get(
                    url,
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 401:
                    # Try alternative: eBay Finding API (simpler auth)
                    return await self._search_finding_api(query, max_results)
                
                response.raise_for_status()
                data = response.json()
                
                listings = []
                items = data.get("itemSummaries", [])
                
                for item in items:
                    try:
                        listing = self._parse_item(item)
                        if listing:
                            listings.append(listing)
                    except Exception as e:
                        logger.warning(f"Error parsing eBay item: {e}")
                        continue
                
                return {
                    "market_listings": listings,
                    "salvage_hits": [],
                    "external_links": [],
                    "error": None
                }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"eBay API HTTP error: {e}")
            return {
                "market_listings": [],
                "salvage_hits": [],
                "external_links": [],
                "error": f"eBay API error: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"eBay search error: {e}")
            return {
                "market_listings": [],
                "salvage_hits": [],
                "external_links": [],
                "error": str(e)
            }
    
    async def _search_finding_api(self, query: str, max_results: int) -> Dict[str, Any]:
        """
        Fallback to eBay Finding API (simpler, no OAuth required).
        """
        try:
            url = "https://svcs.ebay.com/services/search/FindingService/v1"
            
            params = {
                "OPERATION-NAME": "findItemsByKeywords",
                "SERVICE-VERSION": "1.0.0",
                "SECURITY-APPNAME": self.app_id,
                "RESPONSE-DATA-FORMAT": "JSON",
                "REST-PAYLOAD": "",
                "keywords": query,
                "paginationInput.entriesPerPage": min(max_results, settings.max_results_per_source),
            }
            
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                listings = []
                items = data.get("findItemsByKeywordsResponse", [{}])[0].get("searchResult", [{}])[0].get("item", [])
                
                for item in items:
                    try:
                        listing = self._parse_finding_item(item)
                        if listing:
                            listings.append(listing)
                    except Exception as e:
                        logger.warning(f"Error parsing eBay Finding item: {e}")
                        continue
                
                return {
                    "market_listings": listings,
                    "salvage_hits": [],
                    "external_links": [],
                    "error": None
                }
        
        except Exception as e:
            logger.error(f"eBay Finding API error: {e}")
            return {
                "market_listings": [],
                "salvage_hits": [],
                "external_links": [],
                "error": str(e)
            }
    
    def _parse_item(self, item: Dict[str, Any]) -> Optional[MarketListing]:
        """Parse eBay Browse API item."""
        try:
            title = item.get("title", "")
            price_info = item.get("price", {})
            price_value = price_info.get("value", "0") if isinstance(price_info, dict) else str(price_info)
            
            listing = MarketListing(
                source="ebay",
                title=title,
                price=normalize_price(price_value),
                currency=price_info.get("currency", "USD") if isinstance(price_info, dict) else "USD",
                condition=normalize_condition(item.get("condition", "")),
                url=clean_url(item.get("itemWebUrl", "")),
                part_numbers=extract_part_numbers(title),
                vendor=item.get("seller", {}).get("username", "") if isinstance(item.get("seller"), dict) else None,
                image_url=item.get("image", {}).get("imageUrl", "") if isinstance(item.get("image"), dict) else None
            )
            return listing
        except Exception as e:
            logger.warning(f"Error creating MarketListing from eBay item: {e}")
            return None
    
    def _parse_finding_item(self, item: Dict[str, Any]) -> Optional[MarketListing]:
        """Parse eBay Finding API item."""
        try:
            title = item.get("title", [""])[0] if isinstance(item.get("title"), list) else item.get("title", "")
            price_info = item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0]
            price_value = price_info.get("__value__", "0") if isinstance(price_info, dict) else str(price_info)
            
            listing = MarketListing(
                source="ebay",
                title=title,
                price=normalize_price(price_value),
                currency=price_info.get("@currencyId", "USD") if isinstance(price_info, dict) else "USD",
                condition=normalize_condition(item.get("condition", [{}])[0].get("conditionDisplayName", [""])[0] if isinstance(item.get("condition"), list) else ""),
                url=clean_url(item.get("viewItemURL", [""])[0] if isinstance(item.get("viewItemURL"), list) else item.get("viewItemURL", "")),
                part_numbers=extract_part_numbers(title),
                vendor=item.get("sellerInfo", [{}])[0].get("sellerUserName", [""])[0] if isinstance(item.get("sellerInfo"), list) else None,
                image_url=item.get("galleryURL", [""])[0] if isinstance(item.get("galleryURL"), list) else None
            )
            return listing
        except Exception as e:
            logger.warning(f"Error creating MarketListing from eBay Finding item: {e}")
            return None
