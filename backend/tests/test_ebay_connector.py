"""Tests for eBay Browse API connector with OAuth 2.0."""
import pytest
import respx
import httpx
from unittest.mock import patch
from app.ingestion.ebay import eBayConnector, _oauth_token, _oauth_token_expires
import app.ingestion.ebay as ebay_module


@pytest.fixture(autouse=True)
def reset_oauth_cache():
    """Reset the module-level OAuth cache before each test."""
    ebay_module._oauth_token = None
    ebay_module._oauth_token_expires = 0.0
    yield
    ebay_module._oauth_token = None
    ebay_module._oauth_token_expires = 0.0


class TestEBayConnectorWithoutCredentials:
    """Tests for when eBay API keys are not configured."""

    @pytest.mark.asyncio
    async def test_generates_links_without_credentials(self):
        with patch.object(eBayConnector, "_has_credentials", new_callable=lambda: property(lambda self: False)):
            connector = eBayConnector()
            connector.app_id = None
            connector.cert_id = None
            result = await connector.search("brake pads")

        assert result["error"] is None
        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []
        link = result["external_links"][0]
        assert "ebay.com" in link.url
        assert link.source == "ebay"

    @pytest.mark.asyncio
    async def test_generates_per_part_number_links(self):
        with patch.object(eBayConnector, "_has_credentials", new_callable=lambda: property(lambda self: False)):
            connector = eBayConnector()
            connector.app_id = None
            connector.cert_id = None
            result = await connector.search("brake pads", part_numbers=["BP1234"])

        # Should have main link + per-part-number link
        assert len(result["external_links"]) >= 2
        urls = [link.url for link in result["external_links"]]
        assert any("BP1234" in u for u in urls)


class TestEBayConnectorWithCredentials:
    """Tests for when eBay API keys are configured (mocked HTTP)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_oauth_token_request(self):
        # Mock OAuth token endpoint
        respx.post("https://api.sandbox.ebay.com/identity/v1/oauth2/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "test-token-123",
                "expires_in": 7200,
                "token_type": "Application Access Token",
            })
        )

        # Mock Browse API search
        respx.get("https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search").mock(
            return_value=httpx.Response(200, json={"itemSummaries": []})
        )

        connector = eBayConnector()
        connector.app_id = "test-app-id"
        connector.cert_id = "test-cert-id"
        result = await connector.search("brake pads")

        assert result["error"] is None
        assert result["market_listings"] == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_parses_browse_api_items(self, sample_ebay_item):
        respx.post("https://api.sandbox.ebay.com/identity/v1/oauth2/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "test-token-123",
                "expires_in": 7200,
            })
        )

        respx.get("https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search").mock(
            return_value=httpx.Response(200, json={
                "itemSummaries": [sample_ebay_item]
            })
        )

        connector = eBayConnector()
        connector.app_id = "test-app-id"
        connector.cert_id = "test-cert-id"
        result = await connector.search("brake pads")

        assert len(result["market_listings"]) == 1
        listing = result["market_listings"][0]
        assert listing.source == "ebay"
        assert listing.price == 42.99
        assert listing.listing_type == "buy_it_now"
        assert listing.shipping_cost == 5.99
        assert listing.vendor == "autoparts_seller"

    @respx.mock
    @pytest.mark.asyncio
    async def test_auction_listing_type(self, sample_ebay_item_auction):
        respx.post("https://api.sandbox.ebay.com/identity/v1/oauth2/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "test-token-123",
                "expires_in": 7200,
            })
        )

        respx.get("https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search").mock(
            return_value=httpx.Response(200, json={
                "itemSummaries": [sample_ebay_item_auction]
            })
        )

        connector = eBayConnector()
        connector.app_id = "test-app-id"
        connector.cert_id = "test-cert-id"
        result = await connector.search("timing belt")

        listing = result["market_listings"][0]
        assert listing.listing_type == "auction"

    @respx.mock
    @pytest.mark.asyncio
    async def test_api_error_falls_back_to_links(self):
        respx.post("https://api.sandbox.ebay.com/identity/v1/oauth2/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "test-token-123",
                "expires_in": 7200,
            })
        )

        respx.get("https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search").mock(
            return_value=httpx.Response(500)
        )

        connector = eBayConnector()
        connector.app_id = "test-app-id"
        connector.cert_id = "test-cert-id"
        result = await connector.search("brake pads")

        assert result["error"] is not None
        assert len(result["external_links"]) >= 1
        assert "ebay.com" in result["external_links"][0].url
