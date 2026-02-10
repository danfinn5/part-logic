"""
Pydantic schemas for search API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class MarketListing(BaseModel):
    """Unified market listing from eBay, RockAuto, etc."""
    source: str
    title: str
    price: float
    currency: str = "USD"
    condition: Optional[str] = None
    url: str
    part_numbers: List[str] = Field(default_factory=list)
    vendor: Optional[str] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None
    shipping_cost: Optional[float] = None
    listing_type: Optional[str] = None  # "auction", "buy_it_now", "classified"


class SalvageHit(BaseModel):
    """Salvage yard inventory result."""
    source: str = "row52"
    yard_name: str
    yard_location: str
    vehicle: str  # e.g., "2015 Honda Civic"
    url: str
    last_seen: Optional[str] = None
    part_description: Optional[str] = None


class ExternalLink(BaseModel):
    """External link to search results on another site."""
    label: str
    url: str
    source: str = "carpart"
    category: Optional[str] = None  # "new_parts", "used_salvage", "repair_resources"


class SourceStatus(BaseModel):
    """Status of a source query."""
    source: str
    status: Literal["ok", "error", "cached"]
    details: Optional[str] = None
    result_count: int = 0


class SearchResults(BaseModel):
    """Structured search results container."""
    market_listings: List[MarketListing] = Field(default_factory=list)
    salvage_hits: List[SalvageHit] = Field(default_factory=list)
    external_links: List[ExternalLink] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Response from /search endpoint."""
    query: str
    extracted_part_numbers: List[str] = Field(default_factory=list)
    results: SearchResults = Field(default_factory=SearchResults)
    sources_queried: List[SourceStatus] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    cached: bool = False
