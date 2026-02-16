"""Tests for the interchange expansion module."""

from unittest.mock import AsyncMock, patch

import pytest

from app.utils.cross_reference import CrossRefResult
from app.utils.interchange import (
    _merge_cross_ref_results,
    build_interchange_group,
)
from app.utils.query_analysis import QueryAnalysis, QueryType


class TestMergeCrossRefResults:
    def test_merge_single_result(self):
        results = [
            CrossRefResult(
                source="fcpeuro",
                part_numbers=["ABC123", "DEF456"],
                brands={"Lemforder": ["ABC123"], "Meyle": ["DEF456"]},
                vehicle_hint="Porsche 944",
                part_description="Engine Mount",
            )
        ]
        group = _merge_cross_ref_results("951-375-042-04", results)

        assert group.primary_part_number == "951-375-042-04"
        assert "ABC123" in group.interchange_numbers
        assert "DEF456" in group.interchange_numbers
        assert "Lemforder" in group.brands
        assert "Meyle" in group.brands
        assert group.vehicle_fitment == "Porsche 944"
        assert group.part_description == "Engine Mount"
        assert group.confidence == 0.5  # single source

    def test_merge_multiple_results(self):
        results = [
            CrossRefResult(
                source="fcpeuro",
                part_numbers=["ABC123"],
                brands={"Lemforder": ["ABC123"]},
                vehicle_hint="Porsche 944",
                part_description="Engine Mount",
            ),
            CrossRefResult(
                source="rockauto",
                part_numbers=["ABC123", "GHI789"],
                brands={"Lemforder": ["ABC123"], "URO": ["GHI789"]},
                part_description="Motor Mount",
            ),
        ]
        group = _merge_cross_ref_results("951-375-042-04", results)

        assert group.confidence == 0.7  # two sources
        assert "ABC123" in group.interchange_numbers
        assert "GHI789" in group.interchange_numbers
        assert "URO" in group.brands
        assert group.vehicle_fitment == "Porsche 944"  # from first result

    def test_merge_three_results_high_confidence(self):
        results = [
            CrossRefResult(source="fcpeuro", part_numbers=["A1"]),
            CrossRefResult(source="rockauto", part_numbers=["A2"]),
            CrossRefResult(source="parts-crossreference", part_numbers=["A3"]),
        ]
        group = _merge_cross_ref_results("X1", results)
        assert group.confidence == 0.9

    def test_excludes_primary_from_interchange(self):
        results = [
            CrossRefResult(
                source="fcpeuro",
                part_numbers=["951-375-042-04", "ABC123"],
            ),
        ]
        group = _merge_cross_ref_results("951-375-042-04", results)
        assert "951-375-042-04" not in group.interchange_numbers
        assert "ABC123" in group.interchange_numbers

    def test_empty_results(self):
        group = _merge_cross_ref_results("X1", [])
        assert group.interchange_numbers == []
        assert group.brands == {}
        assert group.confidence == 0.0

    def test_deduplicates_part_numbers(self):
        results = [
            CrossRefResult(source="a", part_numbers=["ABC", "DEF"]),
            CrossRefResult(source="b", part_numbers=["ABC", "GHI"]),
        ]
        group = _merge_cross_ref_results("X1", results)
        assert len(group.interchange_numbers) == 3  # ABC, DEF, GHI (no dupes)

    def test_sources_consulted_tracked(self):
        results = [
            CrossRefResult(source="fcpeuro"),
            CrossRefResult(source="rockauto"),
        ]
        group = _merge_cross_ref_results("X1", results)
        assert "fcpeuro" in group.sources_consulted
        assert "rockauto" in group.sources_consulted


class TestBuildInterchangeGroup:
    @pytest.mark.asyncio
    async def test_returns_none_for_non_part_number_query(self):
        analysis = QueryAnalysis(
            query_type=QueryType.KEYWORDS,
            original_query="brake pads",
        )
        result = await build_interchange_group(analysis)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self):
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )
        with patch("app.utils.interchange.settings") as mock_settings:
            mock_settings.interchange_enabled = False
            result = await build_interchange_group(analysis)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_without_part_numbers(self):
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=[],
        )
        result = await build_interchange_group(analysis)
        assert result is None

    @pytest.mark.asyncio
    async def test_fans_out_to_providers(self):
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )
        fcpeuro_result = CrossRefResult(
            source="fcpeuro",
            part_numbers=["ABC123"],
            brands={"Lemforder": ["ABC123"]},
            vehicle_hint="Porsche 944",
            part_description="Engine Mount",
        )
        rockauto_result = CrossRefResult(source="rockauto")
        crossref_result = CrossRefResult(source="parts-crossreference")

        with (
            patch("app.utils.interchange.enrich_from_fcpeuro", new_callable=AsyncMock, return_value=fcpeuro_result),
            patch("app.utils.interchange.enrich_from_rockauto", new_callable=AsyncMock, return_value=rockauto_result),
            patch(
                "app.utils.interchange.enrich_from_parts_crossref", new_callable=AsyncMock, return_value=crossref_result
            ),
        ):
            result = await build_interchange_group(analysis)

        assert result is not None
        assert result.primary_part_number == "951-375-042-04"
        assert "ABC123" in result.interchange_numbers
        assert "Lemforder" in result.brands

    @pytest.mark.asyncio
    async def test_handles_provider_exceptions(self):
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )
        fcpeuro_result = CrossRefResult(
            source="fcpeuro",
            part_numbers=["ABC123"],
            brands={"Lemforder": ["ABC123"]},
        )

        with (
            patch("app.utils.interchange.enrich_from_fcpeuro", new_callable=AsyncMock, return_value=fcpeuro_result),
            patch(
                "app.utils.interchange.enrich_from_rockauto", new_callable=AsyncMock, side_effect=Exception("timeout")
            ),
            patch(
                "app.utils.interchange.enrich_from_parts_crossref",
                new_callable=AsyncMock,
                side_effect=Exception("refused"),
            ),
        ):
            result = await build_interchange_group(analysis)

        assert result is not None
        assert "ABC123" in result.interchange_numbers

    @pytest.mark.asyncio
    async def test_updates_analysis_with_merged_data(self):
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )
        fcpeuro_result = CrossRefResult(
            source="fcpeuro",
            part_numbers=["ABC123"],
            brands={"Lemforder": ["ABC123"]},
            vehicle_hint="Porsche 944",
            part_description="Engine Mount",
        )

        with (
            patch("app.utils.interchange.enrich_from_fcpeuro", new_callable=AsyncMock, return_value=fcpeuro_result),
            patch(
                "app.utils.interchange.enrich_from_rockauto",
                new_callable=AsyncMock,
                return_value=CrossRefResult(source="rockauto"),
            ),
            patch(
                "app.utils.interchange.enrich_from_parts_crossref",
                new_callable=AsyncMock,
                return_value=CrossRefResult(source="parts-crossreference"),
            ),
        ):
            await build_interchange_group(analysis)

        assert analysis.vehicle_hint == "Porsche 944"
        assert analysis.part_description == "Engine Mount"
        assert "ABC123" in analysis.cross_references
        assert "Lemforder" in analysis.brands_found

    @pytest.mark.asyncio
    async def test_returns_none_when_all_providers_fail(self):
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="951-375-042-04",
            part_numbers=["951-375-042-04"],
        )

        with (
            patch("app.utils.interchange.enrich_from_fcpeuro", new_callable=AsyncMock, side_effect=Exception("fail")),
            patch("app.utils.interchange.enrich_from_rockauto", new_callable=AsyncMock, side_effect=Exception("fail")),
            patch(
                "app.utils.interchange.enrich_from_parts_crossref",
                new_callable=AsyncMock,
                side_effect=Exception("fail"),
            ),
        ):
            result = await build_interchange_group(analysis)

        assert result is None
