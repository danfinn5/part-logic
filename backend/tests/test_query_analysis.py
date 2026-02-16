"""Tests for query analysis utilities."""

from app.utils.query_analysis import QueryType, analyze_query


class TestAnalyzeQuery:
    def test_pure_part_number(self):
        result = analyze_query("951-375-042-04")
        assert result.query_type == QueryType.PART_NUMBER
        assert "951-375-042-04" in result.part_numbers

    def test_part_number_with_prefix(self):
        result = analyze_query("OEM 12345-ABC")
        assert result.query_type == QueryType.PART_NUMBER
        assert len(result.part_numbers) > 0

    def test_part_number_alphanumeric(self):
        result = analyze_query("BP1234")
        assert result.query_type == QueryType.PART_NUMBER

    def test_vehicle_part_query(self):
        result = analyze_query("2015 HONDA CIVIC BRAKE PADS")
        assert result.query_type == QueryType.VEHICLE_PART
        assert result.vehicle_hint is not None
        assert "Honda" in result.vehicle_hint

    def test_vehicle_part_with_year(self):
        result = analyze_query("2020 BMW 328I OIL FILTER")
        assert result.query_type == QueryType.VEHICLE_PART
        assert result.vehicle_hint is not None
        assert "Bmw" in result.vehicle_hint

    def test_keyword_query(self):
        result = analyze_query("BRAKE PADS CERAMIC")
        assert result.query_type == QueryType.KEYWORDS
        assert result.vehicle_hint is None

    def test_keyword_query_simple(self):
        result = analyze_query("BRAKE PADS")
        assert result.query_type == QueryType.KEYWORDS

    def test_preserves_original_query(self):
        result = analyze_query("951-375-042-04")
        assert result.original_query == "951-375-042-04"

    def test_empty_cross_references(self):
        result = analyze_query("BRAKE PADS")
        assert result.cross_references == []
        assert result.brands_found == []

    def test_vehicle_hint_without_year(self):
        result = analyze_query("PORSCHE 944 ENGINE MOUNT")
        assert result.vehicle_hint is not None
        assert "Porsche" in result.vehicle_hint

    def test_multiple_part_numbers(self):
        result = analyze_query("951-375-042-04")
        assert result.query_type == QueryType.PART_NUMBER
        assert len(result.part_numbers) >= 1


class TestQueryTypeDetection:
    """Test edge cases in query type detection."""

    def test_single_word_not_part_number(self):
        result = analyze_query("FILTER")
        assert result.query_type == QueryType.KEYWORDS

    def test_dotted_part_number(self):
        result = analyze_query("123.456")
        assert result.query_type == QueryType.PART_NUMBER

    def test_vehicle_with_model_number(self):
        result = analyze_query("2015 PORSCHE 944 TURBO CLUTCH")
        assert result.query_type == QueryType.VEHICLE_PART
        assert result.vehicle_hint is not None
