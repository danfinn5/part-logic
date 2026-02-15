"""
Pydantic schemas for search API requests and responses.
"""

from typing import Literal

from pydantic import BaseModel, Field


class MarketListing(BaseModel):
    """Unified market listing from eBay, RockAuto, etc."""

    source: str
    title: str
    price: float
    currency: str = "USD"
    condition: str | None = None
    url: str
    part_numbers: list[str] = Field(default_factory=list)
    vendor: str | None = None
    image_url: str | None = None
    brand: str | None = None
    shipping_cost: float | None = None
    listing_type: str | None = None  # "auction", "buy_it_now", "classified"
    matched_interchange: str | None = None  # which interchange PN this matched


class SalvageHit(BaseModel):
    """Salvage yard inventory result."""

    source: str = "row52"
    yard_name: str
    yard_location: str
    vehicle: str  # e.g., "2015 Honda Civic"
    url: str
    last_seen: str | None = None
    part_description: str | None = None


class ExternalLink(BaseModel):
    """External link to search results on another site."""

    label: str
    url: str
    source: str = "carpart"
    category: str | None = None  # "new_parts", "used_salvage", "repair_resources"


class SourceStatus(BaseModel):
    """Status of a source query."""

    source: str
    status: Literal["ok", "error", "cached"]
    details: str | None = None
    result_count: int = 0


class SearchResults(BaseModel):
    """Structured search results container."""

    market_listings: list[MarketListing] = Field(default_factory=list)
    salvage_hits: list[SalvageHit] = Field(default_factory=list)
    external_links: list[ExternalLink] = Field(default_factory=list)


class InterchangeInfo(BaseModel):
    """Interchange part number group information."""

    primary_part_number: str
    interchange_numbers: list[str] = Field(default_factory=list)
    brands_by_number: dict[str, list[str]] = Field(default_factory=dict)  # brand -> [pns]
    confidence: float = 0.0
    sources_consulted: list[str] = Field(default_factory=list)


class BrandSummary(BaseModel):
    """Brand comparison summary for a specific part application."""

    brand: str
    tier: str = "unknown"  # "oem", "premium_aftermarket", "economy", "budget"
    quality_score: float = 0.0  # 1-10
    avg_price: float | None = None
    listing_count: int = 0
    recommendation_note: str | None = None


class CommunitySource(BaseModel):
    """Attribution for community discussion data."""

    title: str
    url: str
    source: str = "reddit"  # "reddit", "forum"
    score: int = 0


class PartIntelligence(BaseModel):
    """Cross-reference and query analysis data."""

    query_type: str = "keywords"  # "part_number", "vehicle_part", "keywords"
    vehicle_hint: str | None = None
    part_description: str | None = None
    cross_references: list[str] = Field(default_factory=list)
    brands_found: list[str] = Field(default_factory=list)
    interchange: InterchangeInfo | None = None
    brand_comparison: list[BrandSummary] = Field(default_factory=list)
    recommendation: str | None = None
    community_sources: list[CommunitySource] = Field(default_factory=list)


class Offer(BaseModel):
    """A single retailer's offer for a part."""

    source: str
    price: float
    shipping_cost: float | None = None
    total_cost: float
    condition: str | None = None
    url: str
    title: str
    image_url: str | None = None
    value_score: float = 0.0


class ListingGroup(BaseModel):
    """A group of offers for the same part across retailers."""

    brand: str
    part_number: str = ""
    tier: str = "unknown"
    quality_score: float = 0.0
    offers: list[Offer] = Field(default_factory=list)
    best_price: float = 0.0
    price_range: dict = Field(default_factory=lambda: {"low": 0.0, "high": 0.0})
    offer_count: int = 0
    best_value_score: float = 0.0


class SearchResponse(BaseModel):
    """Response from /search endpoint."""

    query: str
    extracted_part_numbers: list[str] = Field(default_factory=list)
    results: SearchResults = Field(default_factory=SearchResults)
    grouped_listings: list[ListingGroup] = Field(default_factory=list)
    sources_queried: list[SourceStatus] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    cached: bool = False
    intelligence: PartIntelligence | None = None
