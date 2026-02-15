"""
Ranking and sorting utilities for search results.
"""
from typing import List, Optional
from app.schemas.search import MarketListing, SalvageHit, ExternalLink
from app.utils.query_analysis import QueryAnalysis, QueryType


def _relevance_score(
    listing: MarketListing,
    query: str,
    analysis: Optional[QueryAnalysis] = None,
) -> float:
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

    # Part number match (basic)
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

    # --- Context-aware boosts from QueryAnalysis ---
    if analysis:
        title_upper = listing.title.upper()
        listing_pns_upper = {pn.upper() for pn in listing.part_numbers}

        # Part number match: listing contains searched part numbers or cross-refs
        all_relevant_pns = {pn.upper() for pn in analysis.part_numbers}
        all_relevant_pns.update(pn.upper() for pn in analysis.cross_references)
        if listing_pns_upper & all_relevant_pns:
            score += 15.0
        else:
            # Check if any part numbers appear in the title
            for pn in all_relevant_pns:
                if pn in title_upper:
                    score += 12.0
                    break

        # Vehicle match: boost if listing title mentions the detected vehicle
        if analysis.vehicle_hint:
            vehicle_upper = analysis.vehicle_hint.upper()
            # Check each word of the vehicle hint
            vehicle_words = vehicle_upper.split()
            matched_vehicle = sum(1 for w in vehicle_words if w in title_upper)
            if matched_vehicle == len(vehicle_words):
                score += 10.0
            elif matched_vehicle > 0:
                score += 5.0 * (matched_vehicle / len(vehicle_words))

        # Part description match
        if analysis.part_description:
            desc_upper = analysis.part_description.upper()
            if desc_upper in title_upper:
                score += 8.0
            else:
                desc_words = desc_upper.split()
                matched_desc = sum(1 for w in desc_words if w in title_upper)
                if matched_desc > 0:
                    score += 4.0 * (matched_desc / len(desc_words))

        # Brand match: boost if listing brand matches a cross-ref brand
        if analysis.brands_found and listing.brand:
            listing_brand_upper = listing.brand.upper()
            for brand in analysis.brands_found:
                if brand.upper() == listing_brand_upper:
                    score += 5.0
                    break

    return score


def rank_listings(
    listings: List[MarketListing],
    query: str,
    sort: str = "relevance",
    analysis: Optional[QueryAnalysis] = None,
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
        return sorted(
            listings,
            key=lambda x: _relevance_score(x, query, analysis),
            reverse=True,
        )


def filter_salvage_hits(
    hits: List[SalvageHit],
    analysis: Optional[QueryAnalysis] = None,
) -> List[SalvageHit]:
    """
    Filter salvage hits based on query analysis context.

    When we know the vehicle make (e.g. "Porsche"), remove salvage hits
    for unrelated vehicles (e.g. "2015 Kia Sedona").
    """
    if not analysis or not analysis.vehicle_hint:
        return hits

    # Extract the make from the vehicle hint (first word typically)
    vehicle_upper = analysis.vehicle_hint.upper()
    hint_words = vehicle_upper.split()
    # The make is usually the first non-numeric word
    make = None
    for word in hint_words:
        if not word.isdigit():
            make = word
            break

    if not make:
        return hits

    filtered = []
    for hit in hits:
        vehicle_field = hit.vehicle.upper() if hit.vehicle else ""
        if make in vehicle_field:
            filtered.append(hit)
        # Keep hits where we can't determine the vehicle
        elif not vehicle_field:
            filtered.append(hit)

    return filtered


# Category display order
_CATEGORY_ORDER = {"new_parts": 0, "used_salvage": 1, "repair_resources": 2}


def group_links_by_category(links: List[ExternalLink]) -> List[ExternalLink]:
    """Sort external links grouped by category: New Parts, Used/Salvage, Repair Resources."""
    return sorted(
        links,
        key=lambda x: _CATEGORY_ORDER.get(x.category or "new_parts", 99),
    )
