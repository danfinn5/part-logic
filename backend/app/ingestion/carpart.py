"""
Car-Part.com connector - LINK GENERATOR ONLY (no scraping).
Generates search URLs for Car-Part.com based on query.
"""
from typing import Dict, Any
from urllib.parse import quote_plus
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink
from app.config import settings


class CarPartConnector(BaseConnector):
    """Car-Part.com link generator (no scraping per requirements)."""
    
    def __init__(self):
        super().__init__("carpart")
        self.base_url = "https://www.car-part.com"
    
    async def search(self, query: str, zip_code: str = None, **kwargs) -> Dict[str, Any]:
        """
        Generate a Car-Part.com search URL.
        Does NOT scrape - only returns a link.
        """
        zip_code = zip_code or settings.carpart_default_zip or ""
        
        # Build search URL
        # Car-Part.com uses a search form with various parameters
        # We'll create a generic search URL
        encoded_query = quote_plus(query)
        
        # Car-Part.com search URL format (may need adjustment based on actual site structure)
        search_url = f"{self.base_url}/index.htm"
        
        # If we have a zip code, we can add it to the URL
        # Note: Actual URL structure may vary - this is a best-effort implementation
        if zip_code:
            # Car-Part.com might use query params or a different structure
            # For now, we'll create a simple search link
            search_url = f"{self.base_url}/search.htm?partDescription={encoded_query}&zip={zip_code}"
        else:
            search_url = f"{self.base_url}/search.htm?partDescription={encoded_query}"
        
        external_link = ExternalLink(
            label=f"Search Car-Part.com for '{query}'",
            url=search_url,
            source="carpart"
        )
        
        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": [external_link],
            "error": None
        }
    
    def build_carpart_url(self, query: str, zip_code: str = None) -> str:
        """
        Build Car-Part.com search URL.
        Public method for direct URL generation if needed.
        """
        zip_code = zip_code or settings.carpart_default_zip or ""
        encoded_query = quote_plus(query)
        
        if zip_code:
            return f"{self.base_url}/search.htm?partDescription={encoded_query}&zip={zip_code}"
        else:
            return f"{self.base_url}/search.htm?partDescription={encoded_query}"
