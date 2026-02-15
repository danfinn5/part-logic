"""Tests for cross-reference lookup module.

Tests the vehicle extraction, part description extraction, and
async enrichment function that uses FCP Euro search results.
"""
import pytest
from unittest.mock import patch, AsyncMock

from app.utils.cross_reference import (
    _extract_vehicle_from_title,
    _extract_part_description,
    enrich_with_cross_references,
)
from app.utils.query_analysis import QueryAnalysis, QueryType


# --- Fake FCP Euro HTML for enrich_with_cross_references tests ---

FCPEURO_XREF_HTML = """
<html><body>
<turbo-frame id="product-results" data-gtm-event-event-value='{"ecommerce":{"items":[
  {"item_id":"95137504204","item_name":"Lemforder Engine Mount - Porsche 944 Turbo","item_brand":"Lemforder","price":"89.99"},
  {"item_id":"95137504200","item_name":"Meyle Engine Mount - Porsche 944","item_brand":"Meyle","price":"64.99"},
  {"item_id":"MTC12345","item_name":"URO Engine Mount - Porsche 944 Turbo S","item_brand":"URO","price":"39.99"}
]}}'>
</turbo-frame>
</body></html>
"""

FCPEURO_XREF_HITCARD_HTML = """
<html><body>
<div class="hit">
  <a class="hit__name" href="/engine-mount-lemforder">Lemforder Engine Mount - Porsche 944 Turbo</a>
  <span class="hit__money">$89.99</span>
  <span class="hit__flag">Lemforder</span>
</div>
<div class="hit">
  <a class="hit__name" href="/engine-mount-meyle">Meyle Engine Mount - Porsche 944</a>
  <span class="hit__money">$64.99</span>
  <span class="hit__flag">Meyle</span>
</div>
</body></html>
"""

FCPEURO_EMPTY_HTML = """
<html><body>
<turbo-frame id="product-results">
  <p>No results found.</p>
</turbo-frame>
</body></html>
"""


# --- _extract_vehicle_from_title tests ---

class TestExtractVehicleFromTitle:
    def test_porsche_with_model(self):
        result = _extract_vehicle_from_title("Engine Mount - Porsche 944 Turbo")
        assert result == "Porsche 944 Turbo"

    def test_porsche_model_only(self):
        result = _extract_vehicle_from_title("Lemforder Engine Mount - Porsche 944")
        assert result == "Porsche 944"

    def test_bmw_with_series(self):
        result = _extract_vehicle_from_title("Brake Pad Set - BMW 3 Series E46")
        assert result == "Bmw 3 Series E46"

    def test_mercedes_benz(self):
        result = _extract_vehicle_from_title("Control Arm - Mercedes-Benz W204 C300")
        assert result == "Mercedes-Benz W204 C300"

    def test_volkswagen(self):
        result = _extract_vehicle_from_title("Timing Belt Kit - Volkswagen Golf GTI")
        assert result == "Volkswagen Golf Gti"

    def test_vw_abbreviation(self):
        result = _extract_vehicle_from_title("Oil Filter - VW Jetta")
        assert result == "Vw Jetta"

    def test_make_only_no_model(self):
        result = _extract_vehicle_from_title("Brake Rotor - Audi")
        assert result == "Audi"

    def test_no_vehicle_in_title(self):
        result = _extract_vehicle_from_title("Bosch Brake Pad Set Front Ceramic")
        assert result is None

    def test_empty_string(self):
        result = _extract_vehicle_from_title("")
        assert result is None

    def test_make_at_start_of_title(self):
        result = _extract_vehicle_from_title("BMW 328i Brake Pad Set")
        assert result is not None
        assert "Bmw" in result

    def test_stops_at_delimiter(self):
        """Model extraction should stop at dash delimiters."""
        result = _extract_vehicle_from_title("Porsche 911 - Engine Mount - Front")
        assert result == "Porsche 911"

    def test_stops_at_brand_word(self):
        """Model extraction should stop at known brand words."""
        result = _extract_vehicle_from_title("Volvo S60 MEYLE Control Arm")
        assert result == "Volvo S60"

    def test_case_insensitive(self):
        result = _extract_vehicle_from_title("engine mount - porsche 944 turbo")
        assert result == "Porsche 944 Turbo"

    def test_make_not_at_word_boundary(self):
        """Should not match 'FORD' inside 'BEDFORD'."""
        result = _extract_vehicle_from_title("Bedford Truck Part")
        # 'FORD' is embedded in 'BEDFORD', so boundary check should prevent a match
        assert result is None

    def test_stops_at_for_keyword(self):
        result = _extract_vehicle_from_title("Honda Civic For 2015 Models")
        assert result == "Honda Civic"


# --- _extract_part_description tests ---

class TestExtractPartDescription:
    def test_brand_and_part_before_dash(self):
        result = _extract_part_description("Lemforder Engine Mount - Porsche 944")
        assert result == "Engine Mount"

    def test_part_type_only_before_dash(self):
        result = _extract_part_description("Engine Mount - Porsche 944 Turbo")
        assert result == "Engine Mount"

    def test_brand_and_part_with_pipe(self):
        result = _extract_part_description("Meyle Control Arm | BMW 3 Series")
        assert result == "Control Arm"

    def test_brand_and_part_with_slash(self):
        result = _extract_part_description("Bosch Brake Pad Set / Front Ceramic")
        assert result == "Brake Pad Set"

    def test_multiple_brand_words_stripped(self):
        result = _extract_part_description("Genuine OEM Timing Belt - Honda Civic")
        assert result == "Timing Belt"

    def test_brand_only_first_segment_falls_through(self):
        """When first segment is just a brand, try second segment."""
        result = _extract_part_description("Lemforder - Engine Mount Porsche 944")
        assert result == "Engine Mount Porsche 944"

    def test_no_delimiter(self):
        """Title without delimiters uses entire title as the segment."""
        result = _extract_part_description("Bosch Spark Plug Set")
        assert result == "Spark Plug Set"

    def test_empty_string(self):
        result = _extract_part_description("")
        assert result is None

    def test_brand_only_returns_none(self):
        """If all words are brand/strip words, return None."""
        result = _extract_part_description("Lemforder - Meyle")
        assert result is None

    def test_short_description_rejected(self):
        """Descriptions shorter than 3 chars are rejected."""
        result = _extract_part_description("Bosch OK - BMW 3 Series")
        # "OK" is only 2 chars, so first segment fails; second segment tried
        assert result is not None

    def test_hd_stripped(self):
        result = _extract_part_description("HD Control Arm - BMW E46")
        assert result == "Control Arm"

    def test_performance_stripped(self):
        result = _extract_part_description("Performance Brake Rotor - Porsche 911")
        assert result == "Brake Rotor"

    def test_title_cased_output(self):
        result = _extract_part_description("LEMFORDER ENGINE MOUNT - PORSCHE 944")
        assert result == "Engine Mount"


# --- enrich_with_cross_references tests ---

class TestEnrichWithCrossReferences:
    @pytest.mark.asyncio
    async def test_enriches_from_gtm_json(self):
        """GTM JSON results populate vehicle_hint, part_description, brands, cross-refs."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_XREF_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        assert result is analysis  # modifies in-place and returns same object
        assert result.vehicle_hint == "Porsche 944 Turbo"
        assert result.part_description == "Engine Mount"
        assert "Lemforder" in result.brands_found
        assert "Meyle" in result.brands_found
        assert "Uro" in result.brands_found
        # Cross-refs should contain part numbers found in results
        # that are NOT the input part number
        for xref in result.cross_references:
            assert xref.upper() != "951-375-042-04"
        # enriched_query should be built
        assert result.enriched_query is not None
        assert "951-375-042-04" in result.enriched_query

    @pytest.mark.asyncio
    async def test_enriches_from_hit_cards(self):
        """When GTM JSON is absent, falls back to parsing .hit cards."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_XREF_HITCARD_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        assert result.vehicle_hint == "Porsche 944 Turbo"
        assert result.part_description == "Engine Mount"
        # Hit card brands come from .hit__flag elements
        assert len(result.brands_found) >= 1

    @pytest.mark.asyncio
    async def test_no_enrichment_without_part_numbers(self):
        """If analysis has no part numbers, return unchanged."""
        analysis = QueryAnalysis(
            query_type=QueryType.KEYWORDS,
            original_query="brake pads",
            part_numbers=[],
        )

        result = await enrich_with_cross_references(analysis)

        assert result.vehicle_hint is None
        assert result.part_description is None
        assert result.cross_references == []
        assert result.brands_found == []

    @pytest.mark.asyncio
    async def test_graceful_on_http_error(self):
        """When fetch_html returns non-200, analysis is returned unchanged."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="12345-ABC",
            part_numbers=["12345-ABC"],
        )

        mock_fetch = AsyncMock(return_value=("", 404))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        assert result.vehicle_hint is None
        assert result.part_description is None
        assert result.cross_references == []
        assert result.brands_found == []

    @pytest.mark.asyncio
    async def test_graceful_on_network_exception(self):
        """When fetch_html raises, analysis is returned unchanged."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="12345-ABC",
            part_numbers=["12345-ABC"],
        )

        mock_fetch = AsyncMock(side_effect=Exception("Connection refused"))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        assert result.vehicle_hint is None
        assert result.part_description is None
        assert result.cross_references == []
        assert result.brands_found == []

    @pytest.mark.asyncio
    async def test_no_results_leaves_analysis_unchanged(self):
        """When FCP Euro returns no matching products, analysis unchanged."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="ZZZZZ-99999",
            part_numbers=["ZZZZZ-99999"],
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_EMPTY_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        assert result.vehicle_hint is None
        assert result.part_description is None
        assert result.cross_references == []
        assert result.brands_found == []

    @pytest.mark.asyncio
    async def test_existing_vehicle_hint_preserved(self):
        """If analysis already has vehicle_hint, it should not be overwritten."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
            vehicle_hint="1988 Porsche 944",
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_XREF_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        # Original vehicle hint should be kept since it was already set
        assert result.vehicle_hint == "1988 Porsche 944"
        # But part_description and brands should still be enriched
        assert result.part_description == "Engine Mount"
        assert len(result.brands_found) > 0

    @pytest.mark.asyncio
    async def test_enriched_query_contains_description_and_vehicle(self):
        """enriched_query should combine part number, description, and vehicle."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_XREF_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        assert result.enriched_query is not None
        # Should contain quoted part number
        assert '"951-375-042-04"' in result.enriched_query
        # Should contain lowercased description
        assert "engine mount" in result.enriched_query
        # Should contain lowercased vehicle
        assert "porsche" in result.enriched_query

    @pytest.mark.asyncio
    async def test_cross_references_exclude_input_part_number(self):
        """Cross-references should not include the original query part number."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_XREF_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        # None of the cross-refs should be the input part number
        for xref in result.cross_references:
            assert xref.upper() != "951-375-042-04"

    @pytest.mark.asyncio
    async def test_brands_sorted(self):
        """Brands list should be sorted alphabetically."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_XREF_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        assert result.brands_found == sorted(result.brands_found)

    @pytest.mark.asyncio
    async def test_cross_references_sorted(self):
        """Cross-references list should be sorted alphabetically."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_XREF_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            result = await enrich_with_cross_references(analysis)

        assert result.cross_references == sorted(result.cross_references)

    @pytest.mark.asyncio
    async def test_fetch_called_with_correct_url(self):
        """fetch_html should be called with the FCP Euro search URL."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )

        mock_fetch = AsyncMock(return_value=(FCPEURO_EMPTY_HTML, 200))
        with patch("app.utils.cross_reference.fetch_html", mock_fetch):
            await enrich_with_cross_references(analysis)

        mock_fetch.assert_called_once()
        call_url = mock_fetch.call_args[0][0]
        assert "fcpeuro.com" in call_url
        assert "951-375-042-04" in call_url
