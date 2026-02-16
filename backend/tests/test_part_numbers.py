"""Tests for part number extraction and normalization."""

from app.utils.part_numbers import extract_part_numbers, normalize_part_number, normalize_query


class TestExtractPartNumbers:
    def test_dash_separated(self):
        result = extract_part_numbers("Bosch BP1234-5 brake pads")
        assert "BP1234-5" in result

    def test_oem_prefix(self):
        result = extract_part_numbers("OEM 12345-ABC timing belt")
        assert "12345-ABC" in result

    def test_continuous_alphanumeric(self):
        result = extract_part_numbers("Replace your BP1234X today")
        assert "BP1234X" in result

    def test_dot_separated(self):
        result = extract_part_numbers("Part 123.456 compatible")
        assert "123.456" in result

    def test_empty_input(self):
        assert extract_part_numbers("") == []
        assert extract_part_numbers(None) == []

    def test_no_part_numbers(self):
        result = extract_part_numbers("brake pads for my car")
        assert result == []

    def test_multiple_part_numbers(self):
        result = extract_part_numbers("Fits OEM 12345-ABC and BP987-X")
        assert len(result) >= 2

    def test_case_insensitive(self):
        upper = extract_part_numbers("BP1234-5")
        lower = extract_part_numbers("bp1234-5")
        assert upper == lower


class TestNormalizePartNumber:
    def test_uppercase(self):
        assert normalize_part_number("abc123") == "ABC123"

    def test_strip_spaces(self):
        assert normalize_part_number("  ABC 123  ") == "ABC123"

    def test_preserve_dashes(self):
        assert normalize_part_number("abc-123") == "ABC-123"

    def test_empty(self):
        assert normalize_part_number("") == ""
        assert normalize_part_number(None) == ""


class TestNormalizeQuery:
    def test_uppercase_and_strip(self):
        assert normalize_query("  brake pads  ") == "BRAKE PADS"

    def test_collapse_whitespace(self):
        assert normalize_query("brake   pads") == "BRAKE PADS"

    def test_empty(self):
        assert normalize_query("") == ""
