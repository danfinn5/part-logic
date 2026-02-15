"""
Query analysis utilities for smart connector routing.

Detects whether a query is a part number, vehicle+part description, or generic keywords,
and provides metadata used for connector routing and result ranking.
"""
import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from app.utils.part_numbers import extract_part_numbers


class QueryType(Enum):
    PART_NUMBER = "part_number"    # "951-375-042-04", "BP1234-5"
    VEHICLE_PART = "vehicle_part"  # "2015 Honda Civic brake pads"
    KEYWORDS = "keywords"          # "brake pads ceramic"


@dataclass
class QueryAnalysis:
    """Result of analyzing a search query."""
    query_type: QueryType
    original_query: str
    part_numbers: list[str] = field(default_factory=list)
    vehicle_hint: Optional[str] = None
    part_description: Optional[str] = None
    cross_references: list[str] = field(default_factory=list)
    brands_found: list[str] = field(default_factory=list)
    enriched_query: Optional[str] = None


# Common auto makes for vehicle detection
_MAKES = {
    "ACURA", "ALFA ROMEO", "ASTON MARTIN", "AUDI", "BENTLEY", "BMW", "BUICK",
    "CADILLAC", "CHEVROLET", "CHEVY", "CHRYSLER", "CITROEN", "DACIA", "DAEWOO",
    "DAIHATSU", "DATSUN", "DODGE", "EAGLE", "FERRARI", "FIAT", "FORD",
    "GENESIS", "GEO", "GMC", "HONDA", "HUMMER", "HYUNDAI", "INFINITI",
    "ISUZU", "JAGUAR", "JEEP", "KIA", "LAMBORGHINI", "LANCIA", "LAND ROVER",
    "LEXUS", "LINCOLN", "LOTUS", "MASERATI", "MAZDA", "MCLAREN",
    "MERCEDES", "MERCEDES-BENZ", "MERCURY", "MINI", "MITSUBISHI", "NISSAN",
    "OLDSMOBILE", "OPEL", "PEUGEOT", "PLYMOUTH", "PONTIAC", "PORSCHE",
    "RAM", "RENAULT", "ROLLS-ROYCE", "ROVER", "SAAB", "SATURN", "SCION",
    "SEAT", "SKODA", "SMART", "SUBARU", "SUZUKI", "TESLA", "TOYOTA",
    "TRIUMPH", "VAUXHALL", "VOLKSWAGEN", "VW", "VOLVO",
}

# Year pattern: 4-digit year between 1960-2030
_YEAR_PATTERN = re.compile(r'\b(19[6-9]\d|20[0-3]\d)\b')

# Vehicle pattern: year + make (with optional model words after)
_VEHICLE_PATTERN = re.compile(
    r'\b(19[6-9]\d|20[0-3]\d)\s+([A-Z][A-Z\s-]+?)(?:\s+[A-Z]|$)',
    re.IGNORECASE,
)

# Part number: entire query (after normalization) is one or more part numbers with no
# extra descriptive words. This is stricter than extract_part_numbers which finds
# part numbers embedded in larger text.
_PURE_PART_NUMBER = re.compile(
    r'^[A-Z0-9][A-Z0-9.\-/\s]*$'
)


def _detect_vehicle(query: str) -> Optional[str]:
    """Extract vehicle hint (e.g. 'Porsche 944') from query."""
    query_upper = query.upper()

    # Try year + make pattern
    year_match = _YEAR_PATTERN.search(query_upper)
    if year_match:
        year = year_match.group(1)
        # Look for a make after the year
        after_year = query_upper[year_match.end():].strip()
        for make in sorted(_MAKES, key=len, reverse=True):
            if after_year.startswith(make):
                # Grab model words after make
                rest = after_year[len(make):].strip()
                model_words = []
                for word in rest.split():
                    # Stop at part-description words
                    if word in _PART_KEYWORDS:
                        break
                    model_words.append(word)
                model_str = " ".join(model_words)
                vehicle = f"{year} {make}"
                if model_str:
                    vehicle += f" {model_str}"
                return vehicle.title()

    # No year — check for make + model pattern (e.g. "Porsche 944")
    for make in sorted(_MAKES, key=len, reverse=True):
        idx = query_upper.find(make)
        if idx != -1:
            # Check it's a word boundary
            if idx > 0 and query_upper[idx - 1].isalpha():
                continue
            end = idx + len(make)
            if end < len(query_upper) and query_upper[end].isalpha():
                continue
            # Grab model words after make
            after = query_upper[end:].strip()
            model_words = []
            for word in after.split():
                if word in _PART_KEYWORDS:
                    break
                model_words.append(word)
            model_str = " ".join(model_words)
            if model_str:
                return f"{make} {model_str}".title()
            return make.title()

    return None


# Common part-type keywords that indicate descriptive content, not a part number
_PART_KEYWORDS = {
    "BRAKE", "BRAKES", "PAD", "PADS", "ROTOR", "ROTORS", "CALIPER",
    "ENGINE", "MOUNT", "MOUNTS", "MOTOR", "TRANSMISSION", "CLUTCH",
    "SUSPENSION", "STRUT", "STRUTS", "SHOCK", "SHOCKS", "SPRING", "SPRINGS",
    "FILTER", "OIL", "AIR", "FUEL", "CABIN", "PUMP", "WATER",
    "ALTERNATOR", "STARTER", "BATTERY", "IGNITION", "SPARK", "PLUG", "PLUGS",
    "BELT", "BELTS", "HOSE", "HOSES", "GASKET", "GASKETS", "SEAL", "SEALS",
    "BEARING", "BEARINGS", "BUSHING", "BUSHINGS", "JOINT", "JOINTS",
    "SENSOR", "SWITCH", "VALVE", "THERMOSTAT", "RADIATOR", "CONDENSER",
    "HEADLIGHT", "TAILLIGHT", "MIRROR", "WIPER", "WIPERS",
    "WHEEL", "TIRE", "TIRES", "HUB", "AXLE", "CV", "DRIVESHAFT",
    "EXHAUST", "MUFFLER", "CATALYTIC", "CONVERTER", "MANIFOLD",
    "DOOR", "WINDOW", "FENDER", "BUMPER", "HOOD", "TRUNK", "LATCH",
    "CONTROL", "ARM", "ARMS", "TIE", "ROD", "LINK", "SWAY", "BAR",
    "CERAMIC", "ORGANIC", "METALLIC", "SEMI", "FRONT", "REAR", "LEFT", "RIGHT",
    "UPPER", "LOWER", "INNER", "OUTER", "SET", "KIT", "PAIR", "ASSEMBLY",
}


def _is_part_number_query(query: str, extracted: list[str]) -> bool:
    """
    Determine if the query is essentially a part number search.

    True when the query is just part numbers (possibly with separators),
    not mixed with descriptive English words.
    """
    if not extracted:
        return False

    # Remove all extracted part numbers from the query to see what's left
    remaining = query.upper()
    for pn in extracted:
        remaining = remaining.replace(pn, "")

    # Strip separators and whitespace
    remaining = remaining.strip().strip("-./,").strip()

    # If nothing meaningful remains, it's a pure part number query
    if not remaining:
        return True

    # Check if remaining words are all short connectors or noise
    remaining_words = remaining.split()
    noise_words = {"OR", "AND", "FOR", "THE", "A", "AN", "OEM", "PART", "PN", "P/N", "#", "NO", "NUMBER"}
    meaningful_words = [w for w in remaining_words if w not in noise_words and len(w) > 1]

    # If the only meaningful remaining words are part-description keywords,
    # and part numbers dominate the query, still treat as part number
    if not meaningful_words:
        return True

    # Check if query matches pure part-number-like pattern (digits, letters, dashes, dots)
    if _PURE_PART_NUMBER.match(query.upper().strip()):
        # But make sure it's not all common English words
        words = query.upper().split()
        if all(w in _PART_KEYWORDS or w in _MAKES for w in words):
            return False
        return True

    return False


def analyze_query(query: str) -> QueryAnalysis:
    """
    Analyze a search query to determine its type and extract metadata.

    Returns a QueryAnalysis with query_type, detected part numbers,
    vehicle hints, etc. Cross-references and enriched_query are populated
    later by the cross-reference module.
    """
    normalized = query.upper().strip()
    extracted = extract_part_numbers(normalized)

    # Detect vehicle context
    vehicle_hint = _detect_vehicle(normalized)

    # Determine query type
    if _is_part_number_query(normalized, extracted):
        return QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query=query,
            part_numbers=extracted,
            vehicle_hint=vehicle_hint,
        )

    if vehicle_hint:
        return QueryAnalysis(
            query_type=QueryType.VEHICLE_PART,
            original_query=query,
            part_numbers=extracted,
            vehicle_hint=vehicle_hint,
        )

    return QueryAnalysis(
        query_type=QueryType.KEYWORDS,
        original_query=query,
        part_numbers=extracted,
        vehicle_hint=vehicle_hint,
    )
