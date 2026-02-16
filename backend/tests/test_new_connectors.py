"""Tests for the new connectors (AutoZone, O'Reilly, NAPA, LKQ, Advance Auto)."""

from unittest import mock

import pytest


class TestAutoZoneConnector:
    @pytest.mark.asyncio
    async def test_generates_links_when_scrape_disabled(self):
        with mock.patch("app.config.settings.scrape_enabled", False):
            from app.ingestion.autozone import AutoZoneConnector

            connector = AutoZoneConnector()
            result = await connector.search("brake pads")

            assert result["error"] is None
            assert result["market_listings"] == []
            assert len(result["external_links"]) >= 1
            assert "autozone.com" in result["external_links"][0].url

    @pytest.mark.asyncio
    async def test_source_name(self):
        from app.ingestion.autozone import AutoZoneConnector

        assert AutoZoneConnector().source_name == "autozone"

    @pytest.mark.asyncio
    async def test_part_number_links(self):
        with mock.patch("app.config.settings.scrape_enabled", False):
            from app.ingestion.autozone import AutoZoneConnector

            connector = AutoZoneConnector()
            result = await connector.search("brake pads", part_numbers=["BP100"])

            assert len(result["external_links"]) == 2
            urls = [link.url for link in result["external_links"]]
            assert any("BP100" in u for u in urls)


class TestOReillyConnector:
    @pytest.mark.asyncio
    async def test_generates_links_when_scrape_disabled(self):
        with mock.patch("app.config.settings.scrape_enabled", False):
            from app.ingestion.oreilly import OReillyConnector

            connector = OReillyConnector()
            result = await connector.search("oil filter")

            assert result["error"] is None
            assert len(result["external_links"]) >= 1
            assert "oreillyauto.com" in result["external_links"][0].url

    @pytest.mark.asyncio
    async def test_source_name(self):
        from app.ingestion.oreilly import OReillyConnector

        assert OReillyConnector().source_name == "oreilly"


class TestNAPAConnector:
    @pytest.mark.asyncio
    async def test_generates_links_when_scrape_disabled(self):
        with mock.patch("app.config.settings.scrape_enabled", False):
            from app.ingestion.napa import NAPAConnector

            connector = NAPAConnector()
            result = await connector.search("spark plugs")

            assert result["error"] is None
            assert len(result["external_links"]) >= 1
            assert "napaonline.com" in result["external_links"][0].url

    @pytest.mark.asyncio
    async def test_source_name(self):
        from app.ingestion.napa import NAPAConnector

        assert NAPAConnector().source_name == "napa"


class TestLKQConnector:
    @pytest.mark.asyncio
    async def test_generates_links_when_scrape_disabled(self):
        with mock.patch("app.config.settings.scrape_enabled", False):
            from app.ingestion.lkq import LKQConnector

            connector = LKQConnector()
            result = await connector.search("headlight assembly")

            assert result["error"] is None
            assert len(result["external_links"]) >= 1
            link = result["external_links"][0]
            assert "lkqonline.com" in link.url
            assert link.category == "used_parts"

    @pytest.mark.asyncio
    async def test_source_name(self):
        from app.ingestion.lkq import LKQConnector

        assert LKQConnector().source_name == "lkq"


class TestAdvanceAutoConnector:
    @pytest.mark.asyncio
    async def test_generates_links_when_scrape_disabled(self):
        with mock.patch("app.config.settings.scrape_enabled", False):
            from app.ingestion.advanceauto import AdvanceAutoConnector

            connector = AdvanceAutoConnector()
            result = await connector.search("alternator")

            assert result["error"] is None
            assert len(result["external_links"]) >= 1
            assert "advanceautoparts.com" in result["external_links"][0].url

    @pytest.mark.asyncio
    async def test_source_name(self):
        from app.ingestion.advanceauto import AdvanceAutoConnector

        assert AdvanceAutoConnector().source_name == "advanceauto"
