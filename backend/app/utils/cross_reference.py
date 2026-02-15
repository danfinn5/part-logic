"""
Cross-reference lookup for part number enrichment.

Provider pattern: each source (FCP Euro, RockAuto, parts-crossreference.com)
returns a CrossRefResult. The interchange module merges them.

Legacy enrich_with_cross_references() still works for backward compatibility,
using only FCP Euro.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.utils.part_numbers import extract_part_numbers
from app.utils.query_analysis import QueryAnalysis
from app.utils.scraping import fetch_html

logger = logging.getLogger(__name__)

# Common aftermarket brand names to look for in results
_KNOWN_BRANDS = {
    "LEMFORDER",
    "LEMFÖRDER",
    "MEYLE",
    "FEBI",
    "BILSTEIN",
    "SACHS",
    "BOGE",
    "MOOG",
    "TRW",
    "DELPHI",
    "BOSCH",
    "DENSO",
    "NGK",
    "MANN",
    "MAHLE",
    "HENGST",
    "BREMBO",
    "ATE",
    "EBC",
    "HAWK",
    "STOPTECH",
    "CENTRIC",
    "GENUINE",
    "OEM",
    "OES",
    "VALEO",
    "LUK",
    "INA",
    "SKF",
    "FAG",
    "GATES",
    "CONTINENTAL",
    "DAYCO",
    "DORMAN",
    "STANDARD",
    "BECK ARNLEY",
    "URO",
    "REIN",
    "CORTECO",
    "ELRING",
    "VICTOR REINZ",
    "AJUSA",
    "NISSENS",
    "BEHR",
    "HELLA",
    "OSRAM",
    "PHILIPS",
    "DEPO",
    "CARDONE",
    "MOTORCRAFT",
    "AC DELCO",
    "ACDELCO",
    "MOPAR",
    "KAYABA",
    "KYB",
    "MONROE",
    "TOKICO",
    "KONI",
    "ZIMMERMANN",
    "TEXTAR",
    "PAGID",
    "JURID",
    "MINTEX",
    "PIERBURG",
    "VDO",
    "SIEMENS",
}

# Words to strip when extracting part descriptions from titles
_BRAND_STRIP = _KNOWN_BRANDS | {"NEW", "OE", "REPLACEMENT", "PREMIUM", "HD", "HEAVY DUTY", "PERFORMANCE", "STOCK"}

# Part-type words that indicate we've passed the model and into the part description
_PART_TYPE_WORDS = {
    "ENGINE",
    "MOUNT",
    "MOUNTS",
    "MOTOR",
    "BRAKE",
    "BRAKES",
    "PAD",
    "PADS",
    "ROTOR",
    "ROTORS",
    "CALIPER",
    "CLUTCH",
    "TRANSMISSION",
    "SUSPENSION",
    "STRUT",
    "STRUTS",
    "SHOCK",
    "SHOCKS",
    "SPRING",
    "SPRINGS",
    "FILTER",
    "OIL",
    "AIR",
    "FUEL",
    "PUMP",
    "WATER",
    "ALTERNATOR",
    "STARTER",
    "BELT",
    "BELTS",
    "HOSE",
    "HOSES",
    "GASKET",
    "GASKETS",
    "SEAL",
    "SEALS",
    "BEARING",
    "BEARINGS",
    "BUSHING",
    "BUSHINGS",
    "SENSOR",
    "SWITCH",
    "VALVE",
    "THERMOSTAT",
    "RADIATOR",
    "CONDENSER",
    "EXHAUST",
    "MUFFLER",
    "MANIFOLD",
    "CONTROL",
    "ARM",
    "ARMS",
    "ASSEMBLY",
    "KIT",
    "HEADLIGHT",
    "TAILLIGHT",
    "MIRROR",
    "WIPER",
    "WIPERS",
    "WHEEL",
    "AXLE",
    "DRIVESHAFT",
    "DOOR",
    "WINDOW",
    "FENDER",
    "BUMPER",
    "HOOD",
    "TRUNK",
    "LATCH",
    "TIMING",
    "STEERING",
    "IGNITION",
    "SPARK",
    "PLUG",
    "PLUGS",
    "CATALYTIC",
    "CONVERTER",
    "SWAY",
    "BAR",
    "LINK",
}

# Vehicle make names for extracting vehicle context from titles
_VEHICLE_MAKES = {
    "ACURA",
    "AUDI",
    "BMW",
    "CHEVROLET",
    "CHRYSLER",
    "DODGE",
    "FERRARI",
    "FIAT",
    "FORD",
    "HONDA",
    "HYUNDAI",
    "INFINITI",
    "JAGUAR",
    "JEEP",
    "KIA",
    "LAMBORGHINI",
    "LAND ROVER",
    "LEXUS",
    "LINCOLN",
    "MASERATI",
    "MAZDA",
    "MERCEDES",
    "MERCEDES-BENZ",
    "MINI",
    "MITSUBISHI",
    "NISSAN",
    "PEUGEOT",
    "PORSCHE",
    "RAM",
    "RENAULT",
    "SAAB",
    "SUBARU",
    "SUZUKI",
    "TESLA",
    "TOYOTA",
    "VOLKSWAGEN",
    "VW",
    "VOLVO",
}


@dataclass
class CrossRefResult:
    """Result from a single cross-reference provider."""

    source: str
    part_numbers: list[str] = field(default_factory=list)
    brands: dict[str, list[str]] = field(default_factory=dict)  # brand -> [part_numbers]
    vehicle_hint: str | None = None
    part_description: str | None = None


def _extract_vehicle_from_title(title: str) -> str | None:
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


def _extract_part_description(title: str) -> str | None:
    """
    Extract the part type description from a product title.

    E.g. "Lemforder Engine Mount - Porsche 944" -> "Engine Mount"
    """
    # Split on common delimiters
    parts = re.split(r"\s*[-|/]\s*", title)
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


def _extract_brand(text: str) -> str | None:
    """Check if text matches a known brand."""
    upper = text.upper().strip()
    if upper in _KNOWN_BRANDS:
        return text.strip().title()
    return None


# --- Provider: FCP Euro ---


async def enrich_from_fcpeuro(part_number: str) -> CrossRefResult:
    """Fetch cross-reference data from FCP Euro search results."""
    result = CrossRefResult(source="fcpeuro")

    try:
        items = await _fetch_fcpeuro_results(part_number)
    except Exception as e:
        logger.warning(f"FCP Euro cross-ref failed for {part_number}: {e}")
        return result

    if not items:
        return result

    pn_upper = part_number.upper()
    brands_map: dict[str, set[str]] = {}

    for item in items:
        title = item.get("title", "")
        brand = item.get("brand", "")
        part_nums = item.get("part_numbers", [])

        # Collect brand and its part numbers
        if brand:
            brand_key = brand.title()
            if brand_key not in brands_map:
                brands_map[brand_key] = set()
            for pn in part_nums:
                brands_map[brand_key].add(pn)
                if pn.upper() != pn_upper:
                    result.part_numbers.append(pn)

        # Extract vehicle context
        if not result.vehicle_hint and title:
            result.vehicle_hint = _extract_vehicle_from_title(title)

        # Extract part description
        if not result.part_description and title:
            result.part_description = _extract_part_description(title)

    result.part_numbers = sorted(set(result.part_numbers))
    result.brands = {k: sorted(v) for k, v in brands_map.items()}
    return result


async def _fetch_fcpeuro_results(part_number: str) -> list[dict]:
    """Fetch search results from FCP Euro for a part number."""
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
                    results.append(
                        {
                            "title": title,
                            "brand": brand,
                            "part_numbers": part_nums,
                        }
                    )
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
            results.append(
                {
                    "title": title,
                    "brand": brand,
                    "part_numbers": part_nums,
                }
            )

    return results


# --- Provider: RockAuto ---


async def enrich_from_rockauto(part_number: str) -> CrossRefResult:
    """Extract cross-reference data from RockAuto search results."""
    result = CrossRefResult(source="rockauto")

    try:
        encoded = quote_plus(part_number)
        url = f"https://www.rockauto.com/en/partsearch/?partnum={encoded}"
        html, status = await fetch_html(url, timeout=10)
        if status != 200:
            return result

        soup = BeautifulSoup(html, "html.parser")

        # RockAuto shows part listings with brand and part numbers
        listings = soup.select("[id^='listingcontainer']")
        pn_upper = part_number.upper()
        brands_map: dict[str, set[str]] = {}

        for listing in listings[:20]:  # cap at 20 results
            # Brand is typically in a bold/link element
            brand_el = listing.select_one("span.listing-final-manufacturer")
            if not brand_el:
                brand_el = listing.select_one(".ra-listing-brand")
            brand = brand_el.get_text(strip=True) if brand_el else ""

            # Part number
            pn_el = listing.select_one("span.listing-final-partnumber")
            if not pn_el:
                pn_el = listing.select_one(".ra-listing-partnumber")
            pn_text = pn_el.get_text(strip=True) if pn_el else ""

            if brand and pn_text:
                brand_key = brand.title()
                if brand_key not in brands_map:
                    brands_map[brand_key] = set()
                brands_map[brand_key].add(pn_text)
                if pn_text.upper() != pn_upper:
                    result.part_numbers.append(pn_text)

            # Try to extract vehicle/part from title elements
            title_el = listing.select_one("span.listing-final-desc")
            if title_el and not result.part_description:
                desc = title_el.get_text(strip=True)
                result.part_description = _extract_part_description(desc)

        result.part_numbers = sorted(set(result.part_numbers))
        result.brands = {k: sorted(v) for k, v in brands_map.items()}

    except Exception as e:
        logger.warning(f"RockAuto cross-ref failed for {part_number}: {e}")

    return result


# --- Provider: parts-crossreference.com ---


async def enrich_from_parts_crossref(part_number: str) -> CrossRefResult:
    """Fetch cross-reference data from parts-crossreference.com."""
    result = CrossRefResult(source="parts-crossreference")

    try:
        encoded = quote_plus(part_number)
        url = f"https://parts-crossreference.com/search?q={encoded}"
        html, status = await fetch_html(url, timeout=10)
        if status != 200:
            return result

        soup = BeautifulSoup(html, "html.parser")
        pn_upper = part_number.upper()
        brands_map: dict[str, set[str]] = {}

        # Look for cross-reference table rows
        rows = soup.select("table tr, .crossref-row, .result-row")
        for row in rows[:30]:
            cells = row.select("td")
            if len(cells) >= 2:
                brand_text = cells[0].get_text(strip=True)
                pn_text = cells[1].get_text(strip=True)
                if brand_text and pn_text and len(pn_text) >= 3:
                    brand_key = brand_text.title()
                    if brand_key not in brands_map:
                        brands_map[brand_key] = set()
                    brands_map[brand_key].add(pn_text)
                    if pn_text.upper() != pn_upper:
                        result.part_numbers.append(pn_text)

        # Also look for any description text
        desc_el = soup.select_one(".part-description, .part-name, h1, h2")
        if desc_el:
            desc_text = desc_el.get_text(strip=True)
            if desc_text and len(desc_text) > 3:
                extracted = _extract_part_description(desc_text)
                if extracted:
                    result.part_description = extracted

        result.part_numbers = sorted(set(result.part_numbers))
        result.brands = {k: sorted(v) for k, v in brands_map.items()}

    except Exception as e:
        logger.warning(f"parts-crossreference.com failed for {part_number}: {e}")

    return result


# --- Legacy interface (backward compatible) ---


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

    primary_pn = analysis.part_numbers[0]

    try:
        result = await enrich_from_fcpeuro(primary_pn)
    except Exception as e:
        logger.warning(f"Cross-reference lookup failed for {primary_pn}: {e}")
        return analysis

    if not result.part_numbers and not result.brands:
        return analysis

    # Extract brands as a flat list
    brands = set()
    for brand in result.brands:
        brand_upper = brand.upper()
        if brand_upper in _KNOWN_BRANDS:
            brands.add(brand.title())
        else:
            brands.add(brand)

    analysis.cross_references = sorted(set(result.part_numbers))
    analysis.brands_found = sorted(brands)

    if result.vehicle_hint and not analysis.vehicle_hint:
        analysis.vehicle_hint = result.vehicle_hint
    if result.part_description and not analysis.part_description:
        analysis.part_description = result.part_description

    # Build enriched query for broad-search connectors
    if analysis.part_description or analysis.vehicle_hint:
        parts = [f'"{primary_pn}"']
        desc_parts = []
        if analysis.part_description:
            desc_parts.append(analysis.part_description.lower())
        if analysis.vehicle_hint:
            desc_parts.append(analysis.vehicle_hint.lower())
        if desc_parts:
            parts.append(" ".join(desc_parts))
        analysis.enriched_query = " ".join(parts)

    return analysis
