"""
Listing grouping: clusters the same part across different retailers
for price comparison and value scoring.

A "group" represents a single product (brand + part number) available
from multiple sources at different prices.
"""

import re

from app.data.brand_knowledge import get_brand_profile
from app.schemas.search import MarketListing


def _normalize_key(s: str) -> str:
    """Normalize a string for grouping key comparison."""
    return re.sub(r"[\s\-\.]+", "", s).upper()


def _grouping_key(listing: MarketListing) -> str | None:
    """
    Generate a grouping key for a listing.
    Returns None if listing can't be meaningfully grouped.
    """
    if listing.brand and listing.part_numbers:
        brand = _normalize_key(listing.brand)
        pn = _normalize_key(listing.part_numbers[0])
        return f"{brand}:{pn}"
    return None


def _total_cost(listing: MarketListing) -> float:
    """Total cost = price + shipping. Used for comparison."""
    shipping = listing.shipping_cost if listing.shipping_cost and listing.shipping_cost > 0 else 0.0
    return listing.price + shipping


def _value_score(listing: MarketListing) -> float:
    """
    Compute a value score for a listing: quality relative to cost.
    Higher is better. Returns 0 if price is invalid.

    Formula: (quality_score * 10) / total_cost
    This gives a "quality points per dollar" metric.
    """
    total = _total_cost(listing)
    if total <= 0:
        return 0.0

    profile = get_brand_profile(listing.brand) if listing.brand else None
    quality = profile["quality_score"] if profile else 5.0  # default to mid-range
    return (quality * 10) / total


def group_listings(listings: list[MarketListing]) -> list[dict]:
    """
    Group listings by (brand, part_number) and compute comparison data.

    Returns a list of group dicts sorted by best value score:
    {
        "brand": str,
        "part_number": str,
        "tier": str,
        "quality_score": float,
        "offers": [
            {
                "source": str,
                "price": float,
                "shipping_cost": float | None,
                "total_cost": float,
                "condition": str | None,
                "url": str,
                "title": str,
                "image_url": str | None,
                "value_score": float,
            }
        ],
        "best_price": float,
        "price_range": {"low": float, "high": float},
        "offer_count": int,
        "best_value_score": float,
    }

    Listings that can't be grouped (no brand or no part number) are
    returned as single-offer groups.
    """
    groups: dict[str, list[MarketListing]] = {}
    ungrouped: list[MarketListing] = []

    for listing in listings:
        if listing.price <= 0:
            continue
        key = _grouping_key(listing)
        if key:
            if key not in groups:
                groups[key] = []
            groups[key].append(listing)
        else:
            ungrouped.append(listing)

    result = []

    for _key, group_listings_list in groups.items():
        # Use first listing as representative for brand/part info
        rep = group_listings_list[0]
        profile = get_brand_profile(rep.brand) if rep.brand else None

        offers = []
        for listing in group_listings_list:
            total = _total_cost(listing)
            offers.append(
                {
                    "source": listing.source,
                    "price": listing.price,
                    "shipping_cost": listing.shipping_cost,
                    "total_cost": round(total, 2),
                    "condition": listing.condition,
                    "url": listing.url,
                    "title": listing.title,
                    "image_url": listing.image_url,
                    "value_score": round(_value_score(listing), 3),
                }
            )

        # Sort offers by total cost (cheapest first)
        offers.sort(key=lambda o: o["total_cost"])

        prices = [o["total_cost"] for o in offers]

        result.append(
            {
                "brand": rep.brand or "Unknown",
                "part_number": rep.part_numbers[0] if rep.part_numbers else "",
                "tier": profile["tier"] if profile else "unknown",
                "quality_score": profile["quality_score"] if profile else 0.0,
                "offers": offers,
                "best_price": min(prices),
                "price_range": {"low": min(prices), "high": max(prices)},
                "offer_count": len(offers),
                "best_value_score": max(o["value_score"] for o in offers),
            }
        )

    # Add ungrouped listings as single-offer groups
    for listing in ungrouped:
        if listing.price <= 0:
            continue
        profile = get_brand_profile(listing.brand) if listing.brand else None
        total = _total_cost(listing)
        vs = _value_score(listing)

        result.append(
            {
                "brand": listing.brand or "Unknown",
                "part_number": listing.part_numbers[0] if listing.part_numbers else "",
                "tier": profile["tier"] if profile else "unknown",
                "quality_score": profile["quality_score"] if profile else 0.0,
                "offers": [
                    {
                        "source": listing.source,
                        "price": listing.price,
                        "shipping_cost": listing.shipping_cost,
                        "total_cost": round(total, 2),
                        "condition": listing.condition,
                        "url": listing.url,
                        "title": listing.title,
                        "image_url": listing.image_url,
                        "value_score": round(vs, 3),
                    }
                ],
                "best_price": round(total, 2),
                "price_range": {"low": round(total, 2), "high": round(total, 2)},
                "offer_count": 1,
                "best_value_score": round(vs, 3),
            }
        )

    # Sort groups by best value score (highest first)
    result.sort(key=lambda g: g["best_value_score"], reverse=True)

    return result


def sort_groups(groups: list[dict], sort: str = "value") -> list[dict]:
    """
    Sort listing groups by different criteria.

    Options:
    - "value": best quality/price ratio (default)
    - "price_asc": lowest total cost first
    - "price_desc": highest total cost first
    - "quality": highest quality score first
    """
    if sort == "price_asc":
        return sorted(groups, key=lambda g: g["best_price"])
    elif sort == "price_desc":
        return sorted(groups, key=lambda g: g["best_price"], reverse=True)
    elif sort == "quality":
        return sorted(groups, key=lambda g: g["quality_score"], reverse=True)
    else:  # "value" default
        return sorted(groups, key=lambda g: g["best_value_score"], reverse=True)
