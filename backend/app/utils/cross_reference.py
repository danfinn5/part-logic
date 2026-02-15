"""
Cross-reference lookup for part number enrichment.

Uses FCP Euro search to discover part descriptions, vehicle fitment,
brand alternatives, and cross-reference part numbers for a given OEM number.
"""
import re
import logging
from typing import Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import json
from app.utils.scraping import fetch_html
from app.utils.part_numbers import extract_part_numbers
from app.utils.query_analysis import QueryAnalysis

logger = logging.getLogger(__name__)

# Common aftermarket brand names to look for in results
_KNOWN_BRANDS = {
    "LEMFORDER", "LEMFÖRDER", "MEYLE", "FEBI", "BILSTEIN", "SACHS", "BOGE",
    "MOOG", "TRW", "DELPHI", "BOSCH", "DENSO", "NGK", "MANN", "MAHLE",
    "HENGST", "BREMBO", "ATE", "EBC", "HAWK", "STOPTECH", "CENTRIC",
    "GENUINE", "OEM", "OES", "VALEO", "LUK", "INA", "SKF", "FAG",
    "GATES", "CONTINENTAL", "DAYCO", "DORMAN", "STANDARD", "BECK ARNLEY",
    "URO", "REIN", "CORTECO", "ELRING", "VICTOR REINZ", "AJUSA",
    "NISSENS", "BEHR", "HELLA", "OSRAM", "PHILIPS", "DEPO",
    "CARDONE", "MOTORCRAFT", "AC DELCO", "ACDELCO", "MOPAR",
    "KAYABA", "KYB", "MONROE", "TOKICO", "KONI",
    "ZIMMERMANN", "TEXTAR", "PAGID", "JURID", "MINTEX",
    "PIERBURG", "VDO", "SIEMENS",
}

# Words to strip when extracting part descriptions from titles
_BRAND_STRIP = _KNOWN_BRANDS | {"NEW", "OE", "REPLACEMENT", "PREMIUM", "HD",
                                  "HEAVY DUTY", "PERFORMANCE", "STOCK"}

# Part-type words that indicate we've passed the model and into the part description
_PART_TYPE_WORDS = {
    "ENGINE", "MOUNT", "MOUNTS", "MOTOR", "BRAKE", "BRAKES", "PAD", "PADS",
    "ROTOR", "ROTORS", "CALIPER", "CLUTCH", "TRANSMISSION", "SUSPENSION",
    "STRUT", "STRUTS", "SHOCK", "SHOCKS", "SPRING", "SPRINGS", "FILTER",
    "OIL", "AIR", "FUEL", "PUMP", "WATER", "ALTERNATOR", "STARTER",
    "BELT", "BELTS", "HOSE", "HOSES", "GASKET", "GASKETS", "SEAL", "SEALS",
    "BEARING", "BEARINGS", "BUSHING", "BUSHINGS", "SENSOR", "SWITCH",
    "VALVE", "THERMOSTAT", "RADIATOR", "CONDENSER", "EXHAUST", "MUFFLER",
    "MANIFOLD", "CONTROL", "ARM", "ARMS", "ASSEMBLY", "KIT",
    "HEADLIGHT", "TAILLIGHT", "MIRROR", "WIPER", "WIPERS",
    "WHEEL", "AXLE", "DRIVESHAFT", "DOOR", "WINDOW", "FENDER", "BUMPER",
    "HOOD", "TRUNK", "LATCH", "TIMING", "STEERING", "IGNITION", "SPARK",
    "PLUG", "PLUGS", "CATALYTIC", "CONVERTER", "SWAY", "BAR", "LINK",
}

# Vehicle make names for extracting vehicle context from titles
_VEHICLE_MAKES = {
    "ACURA", "AUDI", "BMW", "CHEVROLET", "CHRYSLER", "DODGE", "FERRARI",
    "FIAT", "FORD", "HONDA", "HYUNDAI", "INFINITI", "JAGUAR", "JEEP", "KIA",
    "LAMBORGHINI", "LAND ROVER", "LEXUS", "LINCOLN", "MASERATI", "MAZDA",
    "MERCEDES", "MERCEDES-BENZ", "MINI", "MITSUBISHI", "NISSAN", "PEUGEOT",
    "PORSCHE", "RAM", "RENAULT", "SAAB", "SUBARU", "SUZUKI", "TESLA",
    "TOYOTA", "VOLKSWAGEN", "VW", "VOLVO",
}


def _extract_vehicle_from_title(title: str) -> Optional[str]:
    """Extract vehicle make + model from a product title like 'Engine Mount - Porsche 944'."""
    upper = title.upper()
    for make in sorted(_VEHICLE_MAKES, key=len, reverse=True):
        idx = upper.find(make)
        if idx == -1:
            continue
        # Must be at word boundary
        if idx > 0 and upper[idx - 1].isalnum():
            continue
        end = idx + len(make)
        if end < len(upper) and upper[end].isalnum():
            continue
        # Grab model info after make (e.g. "944 Turbo")
        after = upper[end:].strip()
        model_words = []
        for word in after.split():
            # Stop at common delimiters
            if word in ("-", "|", "/", "FOR", "WITH", "AND", "OR"):
                break
            # Stop at brand or part-type words
            if word in _BRAND_STRIP or word in _PART_TYPE_WORDS:
                break
            model_words.append(word)
        model = " ".join(model_words)
        vehicle = f"{make} {model}".strip() if model else make
        return vehicle.title()
    return None


def _extract_part_description(title: str) -> Optional[str]:
    """
    Extract the part type description from a product title.

    E.g. "Lemforder Engine Mount - Porsche 944" -> "Engine Mount"
    """
    # Split on common delimiters
    parts = re.split(r'\s*[-|/]\s*', title)
    if not parts:
        return None

    # The first segment before a delimiter usually has brand + part type
    # or just part type
    segment = parts[0].strip()
    words = segment.upper().split()

    # Remove brand words from the start
    desc_words = []
    for word in words:
        if word in _BRAND_STRIP:
            continue
        desc_words.append(word)

    description = " ".join(desc_words).strip()
    if description and len(description) >= 3:
        return description.title()

    # Try second segment if first was just a brand
    if len(parts) > 1:
        segment = parts[1].strip()
        words = segment.upper().split()
        desc_words = [w for w in words if w not in _BRAND_STRIP]
        description = " ".join(desc_words).strip()
        if description and len(description) >= 3:
            return description.title()

    return None


async def enrich_with_cross_references(analysis: QueryAnalysis) -> QueryAnalysis:
    """
    Enrich a QueryAnalysis with cross-reference data from FCP Euro.

    For part number queries, searches FCP Euro to discover:
    - Part description (e.g. "Engine Mount")
    - Vehicle fitment (e.g. "Porsche 944")
    - Brand alternatives (Lemforder, Meyle, etc.)
    - Cross-reference part numbers

    Modifies the analysis in-place and returns it.
    """
    if not analysis.part_numbers:
        return analysis

    # Use the first (primary) part number for lookup
    primary_pn = analysis.part_numbers[0]

    try:
        results = await _fetch_fcpeuro_results(primary_pn)
    except Exception as e:
        logger.warning(f"Cross-reference lookup failed for {primary_pn}: {e}")
        return analysis

    if not results:
        return analysis

    # Extract intelligence from results
    brands = set()
    cross_refs = set()
    vehicle_hint = analysis.vehicle_hint
    part_description = None

    for item in results:
        title = item.get("title", "")
        brand = item.get("brand", "")
        part_nums = item.get("part_numbers", [])

        # Collect brands
        if brand:
            brand_upper = brand.upper()
            if brand_upper in _KNOWN_BRANDS:
                brands.add(brand.title())
            elif brand:
                brands.add(brand)

        # Collect cross-reference part numbers
        for pn in part_nums:
            pn_upper = pn.upper()
            if pn_upper not in {p.upper() for p in analysis.part_numbers}:
                cross_refs.add(pn)

        # Extract vehicle context from first result's title
        if not vehicle_hint and title:
            vehicle_hint = _extract_vehicle_from_title(title)

        # Extract part description from first result
        if not part_description and title:
            part_description = _extract_part_description(title)

    analysis.cross_references = sorted(cross_refs)
    analysis.brands_found = sorted(brands)
    if vehicle_hint:
        analysis.vehicle_hint = vehicle_hint
    if part_description:
        analysis.part_description = part_description

    # Build enriched query for broad-search connectors
    if part_description or vehicle_hint:
        parts = [f'"{primary_pn}"']
        desc_parts = []
        if part_description:
            desc_parts.append(part_description.lower())
        if vehicle_hint:
            desc_parts.append(vehicle_hint.lower())
        if desc_parts:
            parts.append(" ".join(desc_parts))
        analysis.enriched_query = " ".join(parts)

    return analysis


async def _fetch_fcpeuro_results(part_number: str) -> list[dict]:
    """
    Fetch search results from FCP Euro for a part number.

    Returns a list of dicts with keys: title, brand, price, part_numbers.
    """
    encoded = quote_plus(part_number)
    url = f"https://www.fcpeuro.com/products?keywords={encoded}"

    html, status = await fetch_html(url, timeout=10)
    if status != 200:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Strategy 1: GTM event data (structured JSON)
    frame = soup.select_one("turbo-frame#product-results")
    if frame:
        gtm_raw = frame.get("data-gtm-event-event-value", "")
        if gtm_raw:
            try:
                data = json.loads(gtm_raw)
                items = data.get("ecommerce", {}).get("items", [])
                for item in items:
                    title = item.get("item_name", "")
                    brand = item.get("item_brand", "")
                    part_nums = extract_part_numbers(title)
                    item_id = item.get("item_id", "")
                    if item_id and item_id not in part_nums:
                        part_nums.append(item_id)
                    results.append({
                        "title": title,
                        "brand": brand,
                        "part_numbers": part_nums,
                    })
            except (json.JSONDecodeError, TypeError):
                pass

    if results:
        return results

    # Strategy 2: Parse .hit cards
    hits = soup.select("div.hit, .grid-x.hit")
    for hit in hits:
        name_el = hit.select_one(".hit__name")
        title = name_el.get_text(strip=True) if name_el else ""
        flag_el = hit.select_one(".hit__flag")
        brand = flag_el.get_text(strip=True) if flag_el else ""
        part_nums = extract_part_numbers(title) if title else []
        if title:
            results.append({
                "title": title,
                "brand": brand,
                "part_numbers": part_nums,
            })

    return results
