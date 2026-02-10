"""
eBay Browse API connector with OAuth 2.0 client credentials.

When API keys are configured, queries the Browse API for structured results.
When keys are missing, falls back to generating eBay search links.
"""
import base64
import time
import httpx
from typing import Dict, Any, Optional
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import MarketListing, ExternalLink
from app.config import settings
from app.utils.normalization import normalize_price, normalize_condition, clean_url
from app.utils.part_numbers import extract_part_numbers
import logging

logger = logging.getLogger(__name__)

# Module-level OAuth token cache
_oauth_token: Optional[str] = None
_oauth_token_expires: float = 0.0


class eBayConnector(BaseConnector):
    """eBay Browse API connector with OAuth 2.0."""

    def __init__(self):
        super().__init__("ebay")
        self.app_id = settings.ebay_app_id
        self.cert_id = settings.ebay_cert_id
        self.base_url = (
            "https://api.sandbox.ebay.com" if settings.ebay_sandbox
            else "https://api.ebay.com"
        )

    @property
    def _has_credentials(self) -> bool:
        return bool(self.app_id and self.cert_id)

    async def _get_oauth_token(self) -> Optional[str]:
        """Get OAuth 2.0 token using client credentials grant, with caching."""
        global _oauth_token, _oauth_token_expires

        if _oauth_token and time.time() < _oauth_token_expires:
            return _oauth_token

        if not self._has_credentials:
            return None

        credentials = base64.b64encode(
            f"{self.app_id}:{self.cert_id}".encode()
        ).decode()

        token_url = f"{self.base_url}/identity/v1/oauth2/token"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                token_url,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {credentials}",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": settings.ebay_oauth_scope,
                },
            )
            response.raise_for_status()
            data = response.json()

        _oauth_token = data["access_token"]
        # Cache with 200s safety margin (tokens last 7200s)
        _oauth_token_expires = time.time() + data.get("expires_in", 7200) - 200
        return _oauth_token

    async def search(self, query: str, max_results: int = 20, **kwargs) -> Dict[str, Any]:
        """Search eBay. Uses Browse API when keys are configured, otherwise generates links."""
        if not self._has_credentials:
            return self._generate_links(query, kwargs.get("part_numbers", []))

        try:
            token = await self._get_oauth_token()
            if not token:
                return self._generate_links(query, kwargs.get("part_numbers", []))

            url = f"{self.base_url}/buy/browse/v1/item_summary/search"
            params = {
                "q": query,
                "limit": min(max_results, settings.max_results_per_source),
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=US",
            }

            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()

            listings = []
            for item in data.get("itemSummaries", []):
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)

            return {
                "market_listings": listings,
                "salvage_hits": [],
                "external_links": [],
                "error": None,
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"eBay API HTTP error: {e.response.status_code}")
            # Fall back to link generation on API failure
            result = self._generate_links(query, kwargs.get("part_numbers", []))
            result["error"] = f"eBay API error {e.response.status_code}, returning search links"
            return result
        except Exception as e:
            logger.error(f"eBay search error: {e}")
            result = self._generate_links(query, kwargs.get("part_numbers", []))
            result["error"] = f"eBay API unavailable, returning search links"
            return result

    def _parse_item(self, item: Dict[str, Any]) -> Optional[MarketListing]:
        """Parse a Browse API item summary into a MarketListing."""
        try:
            title = item.get("title", "")
            price_info = item.get("price", {})
            price_value = price_info.get("value", "0") if isinstance(price_info, dict) else "0"

            # Determine listing type from buying options
            buying_options = item.get("buyingOptions", [])
            if "AUCTION" in buying_options:
                listing_type = "auction"
            elif "FIXED_PRICE" in buying_options:
                listing_type = "buy_it_now"
            else:
                listing_type = None

            # Shipping cost
            shipping_cost = None
            shipping_options = item.get("shippingOptions", [])
            if shipping_options:
                ship_cost = shipping_options[0].get("shippingCost", {})
                if isinstance(ship_cost, dict):
                    try:
                        shipping_cost = float(ship_cost.get("value", 0))
                    except (ValueError, TypeError):
                        pass

            return MarketListing(
                source="ebay",
                title=title,
                price=normalize_price(price_value),
                currency=price_info.get("currency", "USD") if isinstance(price_info, dict) else "USD",
                condition=normalize_condition(item.get("condition", "")),
                url=clean_url(item.get("itemWebUrl", "")),
                part_numbers=extract_part_numbers(title),
                vendor=item.get("seller", {}).get("username") if isinstance(item.get("seller"), dict) else None,
                image_url=item.get("image", {}).get("imageUrl") if isinstance(item.get("image"), dict) else None,
                listing_type=listing_type,
                shipping_cost=shipping_cost,
            )
        except Exception as e:
            logger.warning(f"Error parsing eBay item: {e}")
            return None

    def _generate_links(self, query: str, part_numbers: list = None) -> Dict[str, Any]:
        """Generate eBay search links when API is unavailable."""
        encoded = quote_plus(query)
        links = [
            ExternalLink(
                label=f"Search eBay for '{query}'",
                url=f"https://www.ebay.com/sch/i.html?_nkw={encoded}&_sacat=6028",
                source="ebay",
                category="new_parts",
            )
        ]

        for pn in (part_numbers or []):
            encoded_pn = quote_plus(pn)
            links.append(ExternalLink(
                label=f"eBay: {pn}",
                url=f"https://www.ebay.com/sch/i.html?_nkw={encoded_pn}&_sacat=6028",
                source="ebay",
                category="new_parts",
            ))

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }
