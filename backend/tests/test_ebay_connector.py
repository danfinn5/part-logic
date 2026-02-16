"""Tests for eBay link generator connector."""

import pytest

from app.ingestion.ebay import eBayConnector


class TestEBayConnector:
    """Tests for eBay link generation."""

    @pytest.mark.asyncio
    async def test_generates_search_link(self):
        connector = eBayConnector()
        result = await connector.search("brake pads")

        assert result["error"] is None
        assert result["market_listings"] == []
        assert result["salvage_hits"] == []
        assert len(result["external_links"]) >= 1
        link = result["external_links"][0]
        assert "ebay.com" in link.url
        assert "brake+pads" in link.url
        assert link.source == "ebay"
        assert link.category == "new_parts"

    @pytest.mark.asyncio
    async def test_generates_per_part_number_links(self):
        connector = eBayConnector()
        result = await connector.search("brake pads", part_numbers=["BP1234", "BP5678"])

        # Main search link + one per part number
        assert len(result["external_links"]) == 3
        urls = [link.url for link in result["external_links"]]
        assert any("BP1234" in u for u in urls)
        assert any("BP5678" in u for u in urls)

    @pytest.mark.asyncio
    async def test_no_part_numbers(self):
        connector = eBayConnector()
        result = await connector.search("timing belt")

        assert len(result["external_links"]) == 1

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self):
        connector = eBayConnector()
        result = await connector.search("oil filter 2.0T")

        assert result["error"] is None
        assert len(result["external_links"]) >= 1
        assert "ebay.com" in result["external_links"][0].url

    @pytest.mark.asyncio
    async def test_source_name(self):
        connector = eBayConnector()
        assert connector.source_name == "ebay"
