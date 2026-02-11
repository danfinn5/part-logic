"""Tests for connector scraping + fallback behavior.

Tests that each rewritten connector:
1. Parses HTML into real MarketListing/SalvageHit objects when scraping works
2. Falls back to link generation when scraping fails
3. Falls back to link generation when scrape_enabled=False
"""
import pytest
from unittest.mock import patch, AsyncMock

# --- HTML fixture snippets ---

CARPART_HTML = """
<html><body>
<table>
<tr><td>Yard Name</td><td>Location</td><td>Vehicle</td><td>Part</td></tr>
<tr bgcolor="#ffffff">
  <td>U-Pull-It Springfield</td>
  <td>Springfield, IL</td>
  <td>2015 Honda Civic</td>
  <td>Brake Caliper</td>
</tr>
<tr bgcolor="#eeeeee">
  <td>ABC Auto Salvage</td>
  <td>Chicago, IL</td>
  <td>2018 Toyota Camry</td>
  <td>Brake Caliper</td>
</tr>
</table>
</body></html>
"""

ROW52_HTML = """
<html><body>
<div class="vehicle-card">
  <h3 class="vehicle-title">2012 BMW 328i</h3>
  <span class="yard-name">Pick-n-Pull Sacramento</span>
  <span class="yard-location">Sacramento, CA</span>
  <a href="/Vehicle/Detail/12345">View</a>
</div>
<div class="vehicle-card">
  <h3 class="vehicle-title">2014 BMW 535i</h3>
  <span class="yard-name">LKQ Portland</span>
  <span class="yard-location">Portland, OR</span>
  <a href="/Vehicle/Detail/67890">View</a>
</div>
</body></html>
"""

ECSTUNING_HTML = """
<html><body>
<div class="product-card" data-product-id="123">
  <a href="/products/brake-pad-set"><h3 class="product-name">Genuine BMW Brake Pad Set</h3></a>
  <span class="price">$89.99</span>
  <span class="brand">BMW</span>
  <span class="part-number">34-11-6-799-166</span>
  <img src="https://cdn.ecstuning.com/brake-pad.jpg" />
</div>
<div class="product-card" data-product-id="456">
  <a href="/products/brake-rotor"><h3 class="product-name">ATE Brake Rotor Front</h3></a>
  <span class="price">$124.95</span>
  <span class="brand">ATE</span>
  <span class="part-number">34-11-6-855-000</span>
  <img src="https://cdn.ecstuning.com/rotor.jpg" />
</div>
</body></html>
"""

FCPEURO_HTML = """
<html><body>
<div class="product-card" data-product-id="789">
  <a href="/brake-pad-set-genuine-bmw"><h3 class="product-name">Genuine BMW Brake Pad Set - Front</h3></a>
  <span class="price">$79.99</span>
  <span class="brand">Genuine BMW</span>
  <span class="part-number">34116799166</span>
  <img src="https://media.fcpeuro.com/brake-pad.jpg" />
</div>
</body></html>
"""

PARTSOUQ_HTML = """
<html><body>
<div class="part-item">
  <a href="/en/part/34116799166"><span class="part-name">Front Brake Pad Set</span></a>
  <span class="part-number">34-11-6-799-166</span>
  <span class="price">$65.00</span>
  <img src="https://partsouq.com/images/brake.jpg" />
</div>
</body></html>
"""


# --- Helper to mock fetch_html ---

def _mock_fetch(html_content):
    """Return an AsyncMock that resolves to (html, 200)."""
    return AsyncMock(return_value=(html_content, 200))


def _mock_fetch_error():
    """Return an AsyncMock that raises an exception."""
    return AsyncMock(side_effect=Exception("Connection refused"))


# --- CarPart tests ---

class TestCarPartConnector:
    @pytest.mark.asyncio
    async def test_scrape_parses_salvage_hits(self):
        from app.ingestion.carpart import CarPartConnector
        connector = CarPartConnector()
        with patch("app.ingestion.carpart.fetch_html", _mock_fetch(CARPART_HTML)), \
             patch("app.ingestion.carpart.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.carpart_default_zip = ""
            mock_settings.max_results_per_source = 20
            result = await connector.search("brake caliper")

        assert result["error"] is None
        assert len(result["salvage_hits"]) == 2
        hit = result["salvage_hits"][0]
        assert hit.source == "carpart"
        assert hit.yard_name == "U-Pull-It Springfield"
        assert hit.vehicle == "2015 Honda Civic"

    @pytest.mark.asyncio
    async def test_fallback_on_scrape_failure(self):
        from app.ingestion.carpart import CarPartConnector
        connector = CarPartConnector()
        with patch("app.ingestion.carpart.fetch_html", _mock_fetch_error()), \
             patch("app.ingestion.carpart.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.carpart_default_zip = ""
            result = await connector.search("brake caliper")

        assert len(result["external_links"]) >= 1
        assert result["salvage_hits"] == []
        assert "car-part.com" in result["external_links"][0].url

    @pytest.mark.asyncio
    async def test_link_mode_when_scrape_disabled(self):
        from app.ingestion.carpart import CarPartConnector
        connector = CarPartConnector()
        with patch("app.ingestion.carpart.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.carpart_default_zip = ""
            result = await connector.search("brake caliper")

        assert len(result["external_links"]) >= 1
        assert result["salvage_hits"] == []


# --- Row52 tests ---

class TestRow52Connector:
    @pytest.mark.asyncio
    async def test_scrape_parses_salvage_hits(self):
        from app.ingestion.row52 import Row52Connector
        connector = Row52Connector()
        with patch("app.ingestion.row52.fetch_html", _mock_fetch(ROW52_HTML)), \
             patch("app.ingestion.row52.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.carpart_default_zip = ""
            mock_settings.max_results_per_source = 20
            result = await connector.search("BMW brake")

        assert result["error"] is None
        assert len(result["salvage_hits"]) == 2
        hit = result["salvage_hits"][0]
        assert hit.source == "row52"
        assert "BMW" in hit.vehicle
        assert hit.url.startswith("https://row52.com")

    @pytest.mark.asyncio
    async def test_fallback_on_scrape_failure(self):
        from app.ingestion.row52 import Row52Connector
        connector = Row52Connector()
        with patch("app.ingestion.row52.fetch_html", _mock_fetch_error()), \
             patch("app.ingestion.row52.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.carpart_default_zip = ""
            result = await connector.search("BMW brake")

        assert len(result["external_links"]) >= 1
        assert result["salvage_hits"] == []


# --- ECS Tuning tests ---

class TestECSTuningConnector:
    @pytest.mark.asyncio
    async def test_scrape_html_parses_listings(self):
        from app.ingestion.ecstuning import ECSTuningConnector
        connector = ECSTuningConnector()
        with patch("app.ingestion.ecstuning.fetch_json", _mock_fetch_error()), \
             patch("app.ingestion.ecstuning.fetch_html", _mock_fetch(ECSTUNING_HTML)), \
             patch("app.ingestion.ecstuning.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("BMW brake pad")

        assert result["error"] is None
        assert len(result["market_listings"]) == 2
        listing = result["market_listings"][0]
        assert listing.source == "ecstuning"
        assert listing.price == 89.99
        assert listing.condition == "New"
        assert listing.brand == "BMW"

    @pytest.mark.asyncio
    async def test_scrape_api_parses_json(self):
        from app.ingestion.ecstuning import ECSTuningConnector
        connector = ECSTuningConnector()
        api_response = {
            "products": [
                {
                    "name": "Brake Pad Set",
                    "price": "49.99",
                    "url": "https://www.ecstuning.com/b/brake-pad",
                    "brand": "Bosch",
                    "partNumber": "BP1234",
                    "image": "https://cdn.ecstuning.com/img.jpg",
                }
            ]
        }
        with patch("app.ingestion.ecstuning.fetch_json", AsyncMock(return_value=(api_response, 200))), \
             patch("app.ingestion.ecstuning.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("brake pad")

        assert len(result["market_listings"]) == 1
        listing = result["market_listings"][0]
        assert listing.title == "Brake Pad Set"
        assert listing.price == 49.99
        assert listing.brand == "Bosch"
        assert listing.part_numbers == ["BP1234"]

    @pytest.mark.asyncio
    async def test_fallback_on_scrape_failure(self):
        from app.ingestion.ecstuning import ECSTuningConnector
        connector = ECSTuningConnector()
        with patch("app.ingestion.ecstuning.fetch_json", _mock_fetch_error()), \
             patch("app.ingestion.ecstuning.fetch_html", _mock_fetch_error()), \
             patch("app.ingestion.ecstuning.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []


# --- FCP Euro tests ---

class TestFCPEuroConnector:
    @pytest.mark.asyncio
    async def test_scrape_html_parses_listings(self):
        from app.ingestion.fcpeuro import FCPEuroConnector
        connector = FCPEuroConnector()
        with patch("app.ingestion.fcpeuro.fetch_json", _mock_fetch_error()), \
             patch("app.ingestion.fcpeuro.fetch_html", _mock_fetch(FCPEURO_HTML)), \
             patch("app.ingestion.fcpeuro.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("BMW brake pad")

        assert result["error"] is None
        assert len(result["market_listings"]) == 1
        listing = result["market_listings"][0]
        assert listing.source == "fcpeuro"
        assert listing.price == 79.99
        assert "Genuine BMW" in listing.brand

    @pytest.mark.asyncio
    async def test_fallback_on_scrape_failure(self):
        from app.ingestion.fcpeuro import FCPEuroConnector
        connector = FCPEuroConnector()
        with patch("app.ingestion.fcpeuro.fetch_json", _mock_fetch_error()), \
             patch("app.ingestion.fcpeuro.fetch_html", _mock_fetch_error()), \
             patch("app.ingestion.fcpeuro.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []


# --- Partsouq tests ---

class TestPartsouqConnector:
    @pytest.mark.asyncio
    async def test_scrape_parses_listings(self):
        from app.ingestion.partsouq import PartsouqConnector
        connector = PartsouqConnector()
        with patch("app.ingestion.partsouq.fetch_html", _mock_fetch(PARTSOUQ_HTML)), \
             patch("app.ingestion.partsouq.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("34-11-6-799-166")

        assert result["error"] is None
        assert len(result["market_listings"]) == 1
        listing = result["market_listings"][0]
        assert listing.source == "partsouq"
        assert listing.price == 65.0
        assert "34-11-6-799-166" in listing.part_numbers

    @pytest.mark.asyncio
    async def test_fallback_on_scrape_failure(self):
        from app.ingestion.partsouq import PartsouqConnector
        connector = PartsouqConnector()
        with patch("app.ingestion.partsouq.fetch_html", _mock_fetch_error()), \
             patch("app.ingestion.partsouq.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []


# --- Playwright connector tests (mock browser) ---

ROCKAUTO_HTML = """
<html><body>
<table>
<tr class="ra-listing ra-border-bottom">
  <td><span class="listing-text-row-title">Bosch QuietCast Brake Pad Set</span></td>
  <td><span class="ra-price">$32.79</span></td>
  <td><span class="listing-brand">Bosch</span></td>
  <td><a href="/info/brake-pad-123">Details</a></td>
  <td><img src="https://www.rockauto.com/images/brake.jpg" /></td>
</tr>
</table>
</body></html>
"""

PARTSGEEK_HTML = """
<html><body>
<div class="product-card" data-product-id="pg123">
  <a href="/products/brake-pad-set"><h3 class="product-name">Wagner Brake Pad Set</h3></a>
  <span class="price">$28.99</span>
  <span class="brand">Wagner</span>
  <span class="part-number">WG1234</span>
  <img src="https://www.partsgeek.com/images/brake.jpg" />
</div>
</body></html>
"""

AMAZON_HTML = """
<html><body>
<div data-component-type="s-search-result" data-asin="B01ABC1234">
  <h2><a href="/dp/B01ABC1234"><span class="a-text-normal">Bosch BC905 QuietCast Ceramic Brake Pad Set</span></a></h2>
  <span class="a-price"><span class="a-offscreen">$24.97</span></span>
  <img class="s-image" src="https://m.media-amazon.com/images/brake.jpg" />
  <span class="a-icon-alt">4.5 out of 5 stars</span>
</div>
</body></html>
"""


class TestRockAutoConnector:
    @pytest.mark.asyncio
    async def test_scrape_parses_listings(self):
        from app.ingestion.rockauto import RockAutoConnector
        connector = RockAutoConnector()

        # Mock get_page context manager
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.content = AsyncMock(return_value=ROCKAUTO_HTML)
        mock_page.close = AsyncMock()

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_get_page(**kwargs):
            yield mock_page

        with patch("app.ingestion.rockauto.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = True
            mock_settings.max_results_per_source = 20
            with patch("app.utils.browser.get_page", mock_get_page):
                # Patch the import inside _scrape
                with patch.dict("sys.modules", {}):
                    import app.utils.browser
                    with patch.object(app.utils.browser, "get_page", mock_get_page):
                        result = await connector._scrape("brake pads")

        assert result["error"] is None
        assert len(result["market_listings"]) == 1
        listing = result["market_listings"][0]
        assert listing.source == "rockauto"
        assert listing.price == 32.79
        assert listing.brand == "Bosch"

    @pytest.mark.asyncio
    async def test_fallback_when_playwright_disabled(self):
        from app.ingestion.rockauto import RockAutoConnector
        connector = RockAutoConnector()
        with patch("app.ingestion.rockauto.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pads")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []

    @pytest.mark.asyncio
    async def test_fallback_when_scrape_disabled(self):
        from app.ingestion.rockauto import RockAutoConnector
        connector = RockAutoConnector()
        with patch("app.ingestion.rockauto.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = True
            result = await connector.search("brake pads")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []


class TestPartsGeekConnector:
    @pytest.mark.asyncio
    async def test_fallback_when_playwright_disabled(self):
        from app.ingestion.partsgeek import PartsGeekConnector
        connector = PartsGeekConnector()
        with patch("app.ingestion.partsgeek.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pads")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []


class TestAmazonConnector:
    @pytest.mark.asyncio
    async def test_fallback_when_playwright_disabled(self):
        from app.ingestion.amazon import AmazonConnector
        connector = AmazonConnector()
        with patch("app.ingestion.amazon.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pads")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []

    @pytest.mark.asyncio
    async def test_fallback_when_scrape_disabled(self):
        from app.ingestion.amazon import AmazonConnector
        connector = AmazonConnector()
        with patch("app.ingestion.amazon.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = True
            result = await connector.search("brake pads")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []
