"""
Vehicle string normalization for canonical matching and alias_norm.

- Normalize whitespace, punctuation, and drivetrain/trim tokens.
- Produce alias_norm for matching; keep raw string in vehicle_aliases.
"""

import re
from dataclasses import dataclass

# Drivetrain / trim tokens to normalize (alias_norm will use canonical form)
_DRIVETRAIN_ALIASES = {
    "quattro": "quattro",
    "4motion": "4motion",
    "4matic": "4matic",
    "xdrive": "xdrive",
    "awd": "awd",
    "4wd": "4wd",
    "4x4": "4wd",
    "fwd": "fwd",
    "rwd": "rwd",
    "2wd": "2wd",
}

# Common make name variants (raw -> canonical for display; alias_norm is lowercased)
_MAKE_CANONICAL = {
    "vw": "Volkswagen",
    "vw ": "Volkswagen",
    "volkswagen": "Volkswagen",
    "mercedes": "Mercedes-Benz",
    "mercedes-benz": "Mercedes-Benz",
    "mb": "Mercedes-Benz",
    "bmw": "BMW",
    "volvo": "Volvo",
    "audi": "Audi",
    "ford": "Ford",
    "chevrolet": "Chevrolet",
    "chevy": "Chevrolet",
    "gm": "General Motors",
    "honda": "Honda",
    "toyota": "Toyota",
    "nissan": "Nissan",
    "porsche": "Porsche",
    "jaguar": "Jaguar",
    "land rover": "Land Rover",
    "lr": "Land Rover",
}


def normalize_vehicle_string(raw: str) -> str:
    """
    Normalize a vehicle free-text string for alias_norm.
    - Lowercase, strip, collapse whitespace
    - Replace common punctuation (e.g. slashes) with space
    - Normalize known drivetrain/trim tokens to canonical forms
    """
    if not raw or not raw.strip():
        return ""
    s = raw.strip().lower()
    # Replace slashes/dashes used as separators with space
    s = re.sub(r"[\s/\-]+", " ", s)
    s = " ".join(s.split())
    # Tokenize and normalize known drivetrain words
    tokens = s.split()
    out = []
    for t in tokens:
        if t in _DRIVETRAIN_ALIASES:
            out.append(_DRIVETRAIN_ALIASES[t])
        else:
            out.append(t)
    return " ".join(out)


def parse_vehicle_loose(text: str) -> "ParsedVehicle":
    """
    Parse loose vehicle string into year, make_raw, model_raw, trim_raw.
    Does not resolve to canonical vehicle_id; used for ingestion and display.
    """
    norm = normalize_vehicle_string(text)
    year: int | None = None
    make_raw: str | None = None
    model_raw: str | None = None
    trim_raw: str | None = None

    # Year: 4 digits 1960-2030
    year_match = re.search(r"\b(19[6-9]\d|20[0-3]\d)\b", norm)
    if year_match:
        year = int(year_match.group(1))
        # Remove year from string for make/model
        norm = (norm[: year_match.start()] + " " + norm[year_match.end() :]).strip()
        norm = " ".join(norm.split())

    # First token often make (or year already removed)
    tokens = norm.split()
    if tokens:
        make_raw = tokens[0]
        if len(tokens) > 1:
            model_raw = " ".join(tokens[1:])
        # Heuristic: last token might be trim/drivetrain if it's a known one
        if len(tokens) > 2 and tokens[-1] in _DRIVETRAIN_ALIASES:
            trim_raw = tokens[-1]
            model_raw = " ".join(tokens[1:-1]) if len(tokens) > 2 else None

    return ParsedVehicle(
        year=year,
        make_raw=make_raw,
        model_raw=model_raw,
        trim_raw=trim_raw,
        alias_norm=normalize_vehicle_string(text),
        alias_text=text.strip(),
    )


@dataclass
class ParsedVehicle:
    year: int | None
    make_raw: str | None
    model_raw: str | None
    trim_raw: str | None
    alias_norm: str
    alias_text: str
