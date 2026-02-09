"""
Partsouq connector - PLACEHOLDER ONLY (not prioritized for Phase 1).
Returns empty results with a note.
"""
from typing import Dict, Any
from app.ingestion.base import BaseConnector


class PartsouqConnector(BaseConnector):
    """Partsouq connector placeholder (not implemented in Phase 1)."""
    
    def __init__(self):
        super().__init__("partsouq")
    
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Placeholder - returns empty results.
        TODO: Implement Partsouq integration in Phase 2.
        """
        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": [],
            "error": "Partsouq connector not implemented (Phase 2)"
        }
