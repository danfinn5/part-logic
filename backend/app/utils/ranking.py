"""
Ranking and sorting utilities for search results.
"""

import logging
import re

from app.schemas.search import ExternalLink, MarketListing, SalvageHit
from app.services.ai_advisor import AIAdvisorResult
from app.utils.brand_intelligence import get_brand_tier_boost
from app.utils.query_analysis import QueryAnalysis

logger = logging.getLogger(__name__)


def _relevance_score(
    listing: MarketListing,
    query: str,
    analysis: QueryAnalysis | None = None,
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

        # Brand tier boost: prefer higher-quality brands
        if listing.brand:
            score += get_brand_tier_boost(listing.brand, analysis.query_type.value)

    return score


def _value_score(listing: MarketListing) -> float:
    """Quality-per-dollar score for value-based sorting."""
    from app.data.brand_knowledge import get_brand_profile

    total = listing.price + (listing.shipping_cost or 0.0)
    if total <= 0:
        return 0.0
    profile = get_brand_profile(listing.brand) if listing.brand else None
    quality = profile["quality_score"] if profile else 5.0
    return (quality * 10) / total


def rank_listings(
    listings: list[MarketListing],
    query: str,
    sort: str = "relevance",
    analysis: QueryAnalysis | None = None,
) -> list[MarketListing]:
    """
    Rank/sort MarketListing results.

    sort options:
    - "relevance" (default): multi-factor relevance score
    - "price_asc": cheapest first
    - "price_desc": most expensive first
    - "value": best quality-to-price ratio
    """
    if sort == "price_asc":
        return sorted(listings, key=lambda x: x.price if x.price > 0 else float("inf"))
    elif sort == "price_desc":
        return sorted(listings, key=lambda x: x.price, reverse=True)
    elif sort == "value":
        return sorted(listings, key=lambda x: _value_score(x), reverse=True)
    else:
        return sorted(
            listings,
            key=lambda x: _relevance_score(x, query, analysis),
            reverse=True,
        )


# Known models by make — used to detect wrong-vehicle listings
_MAKE_MODELS: dict[str, list[str]] = {
    "porsche": [
        "911",
        "944",
        "924",
        "928",
        "968",
        "356",
        "914",
        "cayenne",
        "panamera",
        "macan",
        "taycan",
        "boxster",
        "cayman",
        "718",
    ],
    "bmw": [
        "e30",
        "e36",
        "e46",
        "e90",
        "e92",
        "f30",
        "g20",
        "e39",
        "e60",
        "f10",
        "e34",
        "x3",
        "x5",
        "x1",
        "x7",
        "m3",
        "m5",
        "z3",
        "z4",
        "i3",
        "i4",
        "ix",
    ],
    "mercedes": [
        "c-class",
        "e-class",
        "s-class",
        "a-class",
        "cla",
        "cls",
        "gle",
        "glc",
        "gla",
        "glb",
        "gls",
        "amg gt",
        "sl",
        "slk",
        "w203",
        "w204",
        "w205",
        "w211",
        "w212",
        "w213",
        "w220",
        "w221",
        "w222",
        "w223",
    ],
    "audi": [
        "a3",
        "a4",
        "a5",
        "a6",
        "a7",
        "a8",
        "q3",
        "q5",
        "q7",
        "q8",
        "tt",
        "r8",
        "rs3",
        "rs4",
        "rs5",
        "rs6",
        "rs7",
        "s3",
        "s4",
        "s5",
        "s6",
        "s7",
    ],
    "volkswagen": [
        "golf",
        "jetta",
        "passat",
        "tiguan",
        "atlas",
        "arteon",
        "beetle",
        "gti",
        "r32",
        "cc",
        "touareg",
        "id.4",
    ],
    "honda": [
        "civic",
        "accord",
        "cr-v",
        "hr-v",
        "pilot",
        "odyssey",
        "fit",
        "insight",
        "element",
        "s2000",
        "prelude",
        "integra",
    ],
    "toyota": [
        "camry",
        "corolla",
        "rav4",
        "highlander",
        "tacoma",
        "tundra",
        "4runner",
        "supra",
        "86",
        "prius",
        "sienna",
        "celica",
        "mr2",
        "land cruiser",
    ],
    "ford": [
        "mustang",
        "f-150",
        "f-250",
        "f-350",
        "explorer",
        "escape",
        "bronco",
        "ranger",
        "edge",
        "fusion",
        "focus",
        "taurus",
        "expedition",
        "maverick",
    ],
    "chevrolet": [
        "camaro",
        "corvette",
        "silverado",
        "tahoe",
        "suburban",
        "equinox",
        "traverse",
        "malibu",
        "impala",
        "blazer",
        "colorado",
        "trailblazer",
    ],
    "subaru": ["wrx", "sti", "outback", "forester", "crosstrek", "impreza", "legacy", "brz", "ascent", "baja"],
    "nissan": [
        "altima",
        "maxima",
        "sentra",
        "370z",
        "350z",
        "300zx",
        "240sx",
        "rogue",
        "pathfinder",
        "frontier",
        "titan",
        "gt-r",
        "leaf",
    ],
    "mazda": ["miata", "mx-5", "mazda3", "mazda6", "cx-5", "cx-9", "cx-30", "rx-7", "rx-8"],
    "volvo": [
        "240",
        "740",
        "940",
        "s40",
        "s60",
        "s80",
        "s90",
        "v40",
        "v60",
        "v70",
        "v90",
        "xc40",
        "xc60",
        "xc90",
        "c30",
        "c70",
        "850",
    ],
    "hyundai": ["elantra", "sonata", "tucson", "santa fe", "kona", "palisade", "veloster", "genesis"],
    "kia": ["forte", "optima", "k5", "sorento", "sportage", "telluride", "soul", "stinger", "seltos", "sedona"],
}

# All known automotive makes (for cross-make filtering)
_KNOWN_MAKES: set[str] = set(_MAKE_MODELS.keys())
_KNOWN_MAKES.update(
    {
        "acura",
        "alfa romeo",
        "buick",
        "cadillac",
        "chrysler",
        "dodge",
        "fiat",
        "genesis",
        "gmc",
        "infiniti",
        "jaguar",
        "jeep",
        "land rover",
        "lexus",
        "lincoln",
        "mini",
        "mitsubishi",
        "ram",
        "saab",
        "scion",
        "tesla",
    }
)

# Aliases: map common alternate names to the canonical make
_MAKE_ALIASES: dict[str, str] = {
    "vw": "volkswagen",
    "chevy": "chevrolet",
    "mercedes-benz": "mercedes",
    "merc": "mercedes",
}

# Short make names that need word-boundary matching to avoid false positives
# (e.g. "ram" in "ceramic", "kia" in "akia", "mini" in "minimize")
_SHORT_MAKES: set[str] = {"ram", "kia", "mini", "gmc", "fiat", "saab"}


def _mentions_make(text_lower: str, make: str) -> bool:
    """Check if text mentions a make, using word boundaries for short names."""
    if make in _SHORT_MAKES or len(make) <= 3:
        return bool(re.search(rf"\b{re.escape(make)}\b", text_lower))
    return make in text_lower


def filter_market_listings(
    listings: list[MarketListing],
    analysis: AIAdvisorResult | None = None,
) -> list[MarketListing]:
    """
    Filter out market listings that are clearly for the wrong vehicle.

    Two-stage filter:
    1. Same-make wrong-model: "Porsche 911" when searching Porsche 944
    2. Cross-make: "Audi A5 Engine Mount" when searching Porsche 944

    Keeps generic/universal listings that don't mention any specific make.
    """
    if not analysis or not analysis.vehicle_make:
        return listings

    make_lower = analysis.vehicle_make.lower().strip()
    # Resolve alias to canonical
    make_canonical = _MAKE_ALIASES.get(make_lower, make_lower)
    model_lower = (analysis.vehicle_model or "").lower().strip()

    # --- Stage 1: Same-make wrong-model filter ---
    if model_lower:
        known_models = _MAKE_MODELS.get(make_canonical, [])
        wrong_models = set()
        for m in known_models:
            if m.lower() != model_lower and m.lower() not in model_lower and model_lower not in m.lower():
                wrong_models.add(m.lower())
    else:
        wrong_models = set()

    # Build the set of "other makes" to check for cross-make contamination
    # Include both canonical names and aliases that map to different makes
    target_names = {make_canonical, make_lower}
    # Also include aliases that resolve to our target
    for alias, canonical in _MAKE_ALIASES.items():
        if canonical == make_canonical:
            target_names.add(alias)

    other_makes = set()
    for m in _KNOWN_MAKES:
        canon = _MAKE_ALIASES.get(m, m)
        if canon != make_canonical:
            other_makes.add(m)
    # Also add aliases that resolve to non-target makes
    for alias, canonical in _MAKE_ALIASES.items():
        if canonical != make_canonical:
            other_makes.add(alias)

    filtered = []
    removed_count = 0
    for listing in listings:
        title_lower = listing.title.lower()

        # --- Stage 1: Same-make wrong-model ---
        if wrong_models and _mentions_make(title_lower, make_canonical):
            # If listing mentions the target model, always keep
            if model_lower and model_lower in title_lower:
                filtered.append(listing)
                continue

            # Check for wrong models
            is_wrong_model = False
            for wrong in wrong_models:
                if re.search(rf"\b{re.escape(wrong)}\b", title_lower):
                    is_wrong_model = True
                    break
            if is_wrong_model:
                removed_count += 1
                continue

        # --- Stage 2: Cross-make filter ---
        # If listing doesn't mention target make, check if it mentions another known make
        mentions_target = any(_mentions_make(title_lower, name) for name in target_names)
        if not mentions_target:
            mentions_other = False
            for other in other_makes:
                if _mentions_make(title_lower, other):
                    mentions_other = True
                    break
            if mentions_other:
                removed_count += 1
                continue

        filtered.append(listing)

    if removed_count > 0:
        logger.info(
            f"Filtered {removed_count} wrong-vehicle market listings "
            f"(target: {analysis.vehicle_make} {analysis.vehicle_model or '(any)'})"
        )

    return filtered


def filter_salvage_hits(
    hits: list[SalvageHit],
    analysis: QueryAnalysis | None = None,
) -> list[SalvageHit]:
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


def group_links_by_category(links: list[ExternalLink]) -> list[ExternalLink]:
    """Sort external links grouped by category: New Parts, Used/Salvage, Repair Resources."""
    return sorted(
        links,
        key=lambda x: _CATEGORY_ORDER.get(x.category or "new_parts", 99),
    )
