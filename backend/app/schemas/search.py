"""
Pydantic schemas for search API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class MarketListing(BaseModel):
    """Unified market listing from eBay, RockAuto, etc."""
    source: Literal["ebay", "rockauto"]
    title: str
    price: float
    currency: str = "USD"
    condition: Optional[str] = None
    url: str
    part_numbers: List[str] = Field(default_factory=list)
    vendor: Optional[str] = None
    image_url: Optional[str] = None


class SalvageHit(BaseModel):
    """Salvage yard inventory result from Row52."""
    source: Literal["row52"] = "row52"
    yard_name: str
    yard_location: str
    vehicle: str  # e.g., "2015 Honda Civic"
    url: str
    last_seen: Optional[str] = None
    part_description: Optional[str] = None


class ExternalLink(BaseModel):
    """External link to search results (e.g., Car-Part.com)."""
    label: str
    url: str
    source: str = "carpart"


class SourceStatus(BaseModel):
    """Status of a source query."""
    source: str
    status: Literal["ok", "error", "cached"]
    details: Optional[str] = None
    result_count: int = 0


class SearchResponse(BaseModel):
    """Response from /search endpoint."""
    query: str
    extracted_part_numbers: List[str] = Field(default_factory=list)
    results: dict = Field(default_factory=dict)
    sources_queried: List[SourceStatus] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    cached: bool = False
