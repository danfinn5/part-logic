"""Tests for all connector link generators.

Verifies that each connector:
1. Returns properly structured results with external links
2. Includes the correct source name and URLs
3. Generates per-part-number links when part_numbers are provided
4. Uses part_description for search-term links when available
"""

from unittest.mock import patch

import pytest


class TestCarPartConnector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.carpart import CarPartConnector

        connector = CarPartConnector()
        result = await connector.search("brake caliper")

        assert result["error"] is None
        assert result["salvage_hits"] == []
        assert result["market_listings"] == []
        assert len(result["external_links"]) == 1
        link = result["external_links"][0]
        assert link.source == "carpart"
        assert "car-part.com" in link.url
        assert link.category == "used_salvage"


class TestRow52Connector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.row52 import Row52Connector

        connector = Row52Connector()
        with patch("app.ingestion.row52.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.carpart_default_zip = ""
            result = await connector.search("BMW brake")

        assert result["error"] is None
        assert result["salvage_hits"] == []
        assert result["market_listings"] == []
        assert len(result["external_links"]) == 1
        link = result["external_links"][0]
        assert link.source == "row52"
        assert "row52.com" in link.url
        assert link.category == "used_salvage"

    @pytest.mark.asyncio
    async def test_includes_zip_code(self):
        from app.ingestion.row52 import Row52Connector

        connector = Row52Connector()
        with patch("app.ingestion.row52.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.carpart_default_zip = ""
            result = await connector.search("BMW brake", zip_code="97201")

        link = result["external_links"][0]
        assert "ZipCode=97201" in link.url
        assert "Distance=50" in link.url


class TestECSTuningConnector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.ecstuning import ECSTuningConnector

        connector = ECSTuningConnector()
        with patch("app.ingestion.ecstuning.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = False
            result = await connector.search("BMW brake pad")

        assert result["error"] is None
        assert result["market_listings"] == []
        assert len(result["external_links"]) >= 1
        link = result["external_links"][0]
        assert link.source == "ecstuning"
        assert "ecstuning.com" in link.url

    @pytest.mark.asyncio
    async def test_part_number_links(self):
        from app.ingestion.ecstuning import ECSTuningConnector

        connector = ECSTuningConnector()
        with patch("app.ingestion.ecstuning.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pad", part_numbers=["34116799166"])

        assert len(result["external_links"]) == 2
        urls = [link.url for link in result["external_links"]]
        assert any("34116799166" in u for u in urls)


class TestFCPEuroConnector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.fcpeuro import FCPEuroConnector

        connector = FCPEuroConnector()
        result = await connector.search("brake pad set")

        assert result["error"] is None
        assert result["market_listings"] == []
        assert len(result["external_links"]) >= 1
        link = result["external_links"][0]
        assert link.source == "fcpeuro"
        assert "fcpeuro.com" in link.url

    @pytest.mark.asyncio
    async def test_part_number_links(self):
        from app.ingestion.fcpeuro import FCPEuroConnector

        connector = FCPEuroConnector()
        result = await connector.search("brake pad", part_numbers=["34116799166", "34116855000"])

        assert len(result["external_links"]) == 3

    @pytest.mark.asyncio
    async def test_uses_part_description(self):
        from app.ingestion.fcpeuro import FCPEuroConnector

        connector = FCPEuroConnector()
        result = await connector.search("34116799166", part_description="brake pads")

        label = result["external_links"][0].label
        assert "brake pads" in label.lower()


class TestPartsouqConnector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.partsouq import PartsouqConnector

        connector = PartsouqConnector()
        with patch("app.ingestion.partsouq.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = False
            result = await connector.search("34116799166")

        assert result["error"] is None
        assert result["market_listings"] == []
        assert len(result["external_links"]) >= 1
        link = result["external_links"][0]
        assert link.source == "partsouq"
        assert "partsouq.com" in link.url


class TestRockAutoConnector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.rockauto import RockAutoConnector

        connector = RockAutoConnector()
        with patch("app.ingestion.rockauto.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pads")

        assert result["error"] is None
        assert result["market_listings"] == []
        assert len(result["external_links"]) >= 1
        link = result["external_links"][0]
        assert link.source == "rockauto"
        assert "rockauto.com" in link.url

    @pytest.mark.asyncio
    async def test_part_number_links(self):
        from app.ingestion.rockauto import RockAutoConnector

        connector = RockAutoConnector()
        with patch("app.ingestion.rockauto.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pads", part_numbers=["BC905"])

        assert len(result["external_links"]) == 2
        urls = [link.url for link in result["external_links"]]
        assert any("BC905" in u for u in urls)


class TestPartsGeekConnector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.partsgeek import PartsGeekConnector

        connector = PartsGeekConnector()
        with patch("app.ingestion.partsgeek.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pads")

        assert result["error"] is None
        assert result["market_listings"] == []
        assert len(result["external_links"]) >= 1
        link = result["external_links"][0]
        assert link.source == "partsgeek"
        assert "partsgeek.com" in link.url


class TestAmazonConnector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.amazon import AmazonConnector

        connector = AmazonConnector()
        with patch("app.ingestion.amazon.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pads")

        assert result["error"] is None
        assert result["market_listings"] == []
        assert len(result["external_links"]) >= 1
        link = result["external_links"][0]
        assert link.source == "amazon"
        assert "amazon.com" in link.url
        assert "automotive" in link.url

    @pytest.mark.asyncio
    async def test_part_number_links(self):
        from app.ingestion.amazon import AmazonConnector

        connector = AmazonConnector()
        with patch("app.ingestion.amazon.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pads", part_numbers=["BC905"])

        assert len(result["external_links"]) == 2


class TesteBayConnector:
    @pytest.mark.asyncio
    async def test_generates_links(self):
        from app.ingestion.ebay import eBayConnector

        connector = eBayConnector()
        result = await connector.search("brake pads")

        assert result["error"] is None
        assert result["market_listings"] == []
        assert len(result["external_links"]) >= 1
        link = result["external_links"][0]
        assert link.source == "ebay"
        assert "ebay.com" in link.url

    @pytest.mark.asyncio
    async def test_part_number_links(self):
        from app.ingestion.ebay import eBayConnector

        connector = eBayConnector()
        result = await connector.search("brake pads", part_numbers=["34116799166"])

        assert len(result["external_links"]) == 2


class TestAllConnectorsRegistered:
    def test_all_connectors_in_registry(self):
        from app.ingestion import get_all_connectors

        connectors = get_all_connectors()
        names = {c.source_name for c in connectors}
        expected = {
            "ebay",
            "rockauto",
            "row52",
            "carpart",
            "partsouq",
            "ecstuning",
            "fcpeuro",
            "amazon",
            "partsgeek",
            "resources",
            "autozone",
            "oreilly",
            "napa",
            "lkq",
            "advanceauto",
        }
        assert expected.issubset(names)

    def test_connector_count(self):
        from app.ingestion import get_all_connectors

        connectors = get_all_connectors()
        assert len(connectors) >= 15
