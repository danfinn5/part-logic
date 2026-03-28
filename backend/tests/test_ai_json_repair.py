"""Tests for AI JSON repair and response parsing."""

from app.services.ai_advisor import _parse_ai_response, _try_repair_json


class TestTryRepairJson:
    def test_truncated_string(self):
        """Repair JSON truncated in the middle of a string value."""
        text = '{"key": "hello wor'
        result = _try_repair_json(text)
        assert result is not None
        assert result["key"] == "hello wor"

    def test_truncated_array(self):
        """Repair JSON truncated inside an array."""
        text = '{"items": ["a", "b"'
        result = _try_repair_json(text)
        assert result is not None
        assert result["items"] == ["a", "b"]

    def test_truncated_nested_objects(self):
        """Repair JSON truncated with nested objects still open."""
        text = '{"vehicle": {"make": "Porsche", "model": "944"}, "recommendations": [{"brand": "Lemforder"'
        result = _try_repair_json(text)
        assert result is not None
        assert result["vehicle"]["make"] == "Porsche"
        assert result["recommendations"][0]["brand"] == "Lemforder"

    def test_trailing_comma(self):
        """Repair JSON with trailing comma before truncation."""
        text = '{"a": 1, "b": 2,'
        result = _try_repair_json(text)
        assert result is not None
        assert result["a"] == 1
        assert result["b"] == 2

    def test_hopeless_input(self):
        """Completely invalid input returns None."""
        result = _try_repair_json("this is not json at all")
        assert result is None

    def test_valid_json_passes_through(self):
        """Already valid JSON is returned as-is."""
        text = '{"key": "value"}'
        result = _try_repair_json(text)
        assert result == {"key": "value"}

    def test_truncated_deeply_nested(self):
        """Repair deeply nested truncation."""
        text = '{"a": {"b": {"c": [1, 2'
        result = _try_repair_json(text)
        assert result is not None
        assert result["a"]["b"]["c"] == [1, 2]

    def test_empty_string(self):
        """Empty string returns None."""
        result = _try_repair_json("")
        assert result is None


class TestParseAiResponse:
    def test_json_code_fence(self):
        """Parse response wrapped in ```json fence."""
        text = '```json\n{"vehicle": {"make": "BMW"}, "recommendations": [], "avoid": [], "notes": "test"}\n```'
        result = _parse_ai_response(text)
        assert result.vehicle_make == "BMW"
        assert result.error is None

    def test_bare_code_fence(self):
        """Parse response wrapped in bare ``` fence."""
        text = '```\n{"vehicle": {"make": "Honda"}, "recommendations": [], "avoid": [], "notes": "test"}\n```'
        result = _parse_ai_response(text)
        assert result.vehicle_make == "Honda"

    def test_valid_json_no_fence(self):
        """Parse clean JSON with no fences."""
        text = '{"vehicle": {"make": "Volvo"}, "part": {"type": "Oil Filter", "oem_part_numbers": ["1275810"]}, "recommendations": [], "avoid": [], "notes": "Good filter."}'
        result = _parse_ai_response(text)
        assert result.vehicle_make == "Volvo"
        assert result.part_type == "Oil Filter"
        assert result.oem_part_numbers == ["1275810"]

    def test_truncated_json_repaired(self):
        """Truncated JSON is repaired and partial data is extracted."""
        text = '{"vehicle": {"make": "Porsche", "model": "944"}, "part": {"type": "Engine Mount", "oem_part_numbers": ["95137504901"]}, "recommendations": [{"rank": 1, "grade": "best_overall", "brand": "Lemforder", "part_number": "123", "title": "Lemforder Mount", "why": "OEM sup'
        result = _parse_ai_response(text)
        assert result.vehicle_make == "Porsche"
        assert result.vehicle_model == "944"
        assert result.oem_part_numbers == ["95137504901"]
        assert len(result.recommendations) >= 1

    def test_garbage_returns_error(self):
        """Completely unparseable text returns error result."""
        result = _parse_ai_response("Sorry, I cannot help with that request.")
        assert result.error is not None
