"""
Ranking and sorting utilities for search results.
"""
from typing import List
from app.schemas.search import MarketListing, ExternalLink


def _relevance_score(listing: MarketListing, query: str) -> float:
    """Score a listing for relevance ranking. Higher is better."""
    score = 0.0
    query_upper = query.upper()

    # Title contains the full query
    if query_upper in listing.title.upper():
        score += 10.0

    # Individual query words in title
    words = query_upper.split()
    if words:
        matched = sum(1 for w in words if w in listing.title.upper())
        score += (matched / len(words)) * 5.0

    # Part number match
    if listing.part_numbers:
        score += 3.0

    # Has image
    if listing.image_url:
        score += 1.0

    # Condition preference: New > Refurbished > Used > Unknown
    condition_scores = {"New": 2.0, "Refurbished": 1.5, "Used": 1.0}
    score += condition_scores.get(listing.condition or "", 0.0)

    # Valid price (not zero)
    if listing.price > 0:
        score += 1.0

    return score


def rank_listings(
    listings: List[MarketListing],
    query: str,
    sort: str = "relevance",
) -> List[MarketListing]:
    """
    Rank/sort MarketListing results.

    sort options:
    - "relevance" (default): multi-factor relevance score
    - "price_asc": cheapest first
    - "price_desc": most expensive first
    """
    if sort == "price_asc":
        return sorted(listings, key=lambda x: x.price if x.price > 0 else float("inf"))
    elif sort == "price_desc":
        return sorted(listings, key=lambda x: x.price, reverse=True)
    else:
        return sorted(listings, key=lambda x: _relevance_score(x, query), reverse=True)


# Category display order
_CATEGORY_ORDER = {"new_parts": 0, "used_salvage": 1, "repair_resources": 2}


def group_links_by_category(links: List[ExternalLink]) -> List[ExternalLink]:
    """Sort external links grouped by category: New Parts, Used/Salvage, Repair Resources."""
    return sorted(
        links,
        key=lambda x: _CATEGORY_ORDER.get(x.category or "new_parts", 99),
    )
