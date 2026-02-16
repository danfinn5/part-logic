"""Tests for part number value_norm (canonical matching)."""

from app.utils.part_numbers import normalize_part_number, part_number_value_norm


def test_value_norm_uppercase_no_spaces():
    """value_norm is uppercase and has no spaces."""
    assert part_number_value_norm("abc 123") == "ABC123"
    assert part_number_value_norm("  xYz-456  ") == "XYZ456"


def test_value_norm_strip_hyphens_default():
    """By default hyphens are stripped so 123-456 and 123456 match."""
    assert part_number_value_norm("123-456") == "123456"
    assert part_number_value_norm("12-34-56") == "123456"


def test_value_norm_preserve_hyphens_when_asked():
    """When strip_hyphens=False, hyphens preserved."""
    assert part_number_value_norm("123-456", strip_hyphens=False) == "123-456"


def test_consistent_value_norm_across_variants():
    """Formatting variants produce same value_norm."""
    a = part_number_value_norm("11427512300")
    b = part_number_value_norm("11427-512-300")
    c = part_number_value_norm("11427 512 300")
    assert a == b == c
    assert a == "11427512300"


def test_normalize_part_number_preserves_dashes():
    """normalize_part_number (display) preserves dashes."""
    assert normalize_part_number("123-456") == "123-456"
    assert normalize_part_number("  abc  ") == "ABC"
