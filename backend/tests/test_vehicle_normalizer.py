"""Tests for vehicle string normalization and parsing."""

from app.utils.vehicle_normalizer import (
    normalize_vehicle_string,
    parse_vehicle_loose,
)


def test_normalize_vehicle_string_same_variants():
    """Same string variants should normalize to same alias_norm."""
    a = normalize_vehicle_string("1995  Volvo  940")
    b = normalize_vehicle_string("1995 Volvo 940")
    c = normalize_vehicle_string("  1995 volvo 940  ")
    assert a == b == c
    assert a == "1995 volvo 940"


def test_normalize_strips_scheme_and_lower():
    """Input is lowercased and whitespace collapsed."""
    assert normalize_vehicle_string("BMW E46 325i") == "bmw e46 325i"
    assert normalize_vehicle_string("   Audi   A4   ") == "audi a4"


def test_normalize_drivetrain_tokens():
    """Drivetrain tokens normalized to consistent forms."""
    # Our current map keeps "quattro", "awd" etc. as-is (lowercase)
    assert "quattro" in normalize_vehicle_string("2005 A4 Quattro")
    assert "awd" in normalize_vehicle_string("Subaru Outback AWD")


def test_parse_vehicle_loose_year():
    """Parse extracts 4-digit year."""
    p = parse_vehicle_loose("1995 Volvo 940")
    assert p.year == 1995
    assert p.alias_text.strip() == "1995 Volvo 940"
    assert "1995" in p.alias_norm or "volvo" in p.alias_norm


def test_parse_vehicle_loose_make_model():
    """Parse extracts make and model."""
    p = parse_vehicle_loose("1998 BMW 3 Series")
    assert p.year == 1998
    assert p.make_raw == "bmw"
    assert p.model_raw is not None
    assert "3" in (p.model_raw or "")


def test_parse_vehicle_loose_empty():
    """Empty or whitespace returns empty norm and None parsed."""
    p = parse_vehicle_loose("")
    assert p.alias_norm == ""
    assert p.year is None
    p2 = parse_vehicle_loose("   ")
    assert p2.alias_norm == ""
