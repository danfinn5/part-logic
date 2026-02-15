"""
Brand intelligence system for comparing part brands.

Groups market listings by brand, merges with static brand profiles,
computes average prices, and generates comparison data.
"""

import logging

from app.data.brand_knowledge import get_brand_profile
from app.schemas.search import BrandSummary, MarketListing
from app.utils.interchange import InterchangeGroup
from app.utils.query_analysis import QueryAnalysis

logger = logging.getLogger(__name__)

# Tier ordering for recommendation sorting (higher = recommended first)
_TIER_RANK = {
    "oem": 4,
    "premium_aftermarket": 3,
    "economy": 2,
    "budget": 1,
    "unknown": 0,
}


def build_brand_comparison(
    listings: list[MarketListing],
    interchange: InterchangeGroup | None = None,
    analysis: QueryAnalysis | None = None,
) -> list[BrandSummary]:
    """
    Build a brand comparison from market listings and interchange data.

    Groups listings by brand, computes average prices, merges with
    static brand profiles, and sorts by recommendation strength.
    """
    # Group listings by brand
    brand_listings: dict[str, list[MarketListing]] = {}
    for listing in listings:
        brand = listing.brand
        if not brand:
            continue
        # Normalize brand name
        brand_key = brand.strip().title()
        if brand_key not in brand_listings:
            brand_listings[brand_key] = []
        brand_listings[brand_key].append(listing)

    # Also include brands from interchange data that may not have listings
    if interchange:
        for brand in interchange.brands:
            brand_key = brand.strip().title()
            if brand_key not in brand_listings:
                brand_listings[brand_key] = []

    if not brand_listings:
        return []

    # Build BrandSummary for each brand
    summaries: list[BrandSummary] = []
    for brand_name, brand_list in brand_listings.items():
        profile = get_brand_profile(brand_name)

        # Compute average price from listings
        prices = [listing.price for listing in brand_list if listing.price > 0]
        avg_price = sum(prices) / len(prices) if prices else None

        tier = profile["tier"] if profile else "unknown"
        quality = profile["quality_score"] if profile else 0.0

        # Generate recommendation note
        note = _generate_recommendation_note(brand_name, profile, avg_price, len(brand_list))

        summaries.append(
            BrandSummary(
                brand=brand_name,
                tier=tier,
                quality_score=quality,
                avg_price=round(avg_price, 2) if avg_price else None,
                listing_count=len(brand_list),
                recommendation_note=note,
            )
        )

    # Sort: premium tiers first, then by quality score, then by value
    summaries.sort(
        key=lambda s: (
            _TIER_RANK.get(s.tier, 0),
            s.quality_score,
        ),
        reverse=True,
    )

    return summaries


def _generate_recommendation_note(
    brand_name: str,
    profile: dict | None,
    avg_price: float | None,
    listing_count: int,
) -> str | None:
    """Generate a brief recommendation note for a brand."""
    if not profile:
        return None

    tier = profile.get("tier", "unknown")
    desc = profile.get("description", "")

    if tier == "oem":
        return f"Factory-original part. {desc}"
    elif tier == "premium_aftermarket":
        note = "OE-quality aftermarket."
        if profile.get("known_for"):
            specialties = ", ".join(profile["known_for"][:3])
            note += f" Known for {specialties}."
        return note
    elif tier == "economy":
        return f"Good value option. {desc}"
    elif tier == "budget":
        return "Lowest cost option. Quality may vary."
    return None


def get_brand_tier_boost(brand_name: str, query_type: str) -> float:
    """
    Get a ranking boost based on brand tier.

    Used by the ranking module to prefer higher-quality brands
    for part_number queries where the user likely wants the right part.
    """
    profile = get_brand_profile(brand_name)
    if not profile:
        return 0.0

    tier = profile.get("tier", "unknown")

    if query_type == "part_number":
        # For part number queries, boost OEM and premium
        boosts = {
            "oem": 3.0,
            "premium_aftermarket": 2.0,
            "economy": 0.5,
            "budget": 0.0,
        }
    else:
        # For keyword/vehicle queries, smaller tier boost
        boosts = {
            "oem": 1.5,
            "premium_aftermarket": 1.0,
            "economy": 0.5,
            "budget": 0.0,
        }

    return boosts.get(tier, 0.0)
