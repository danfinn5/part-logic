"""Tests for connector scraping + fallback behavior.

Tests that each rewritten connector:
1. Parses HTML into real MarketListing/SalvageHit objects when scraping works
2. Falls back to link generation when scraping fails
3. Falls back to link generation when scrape_enabled=False
"""
import pytest
from unittest.mock import patch, AsyncMock
from contextlib import asynccontextmanager

# --- HTML fixture snippets (matching actual site structures) ---

ROW52_HTML = """
<html><body>
<div class="list-row">
  <meta itemprop="year" content="2012" />
  <meta itemprop="make" content="BMW" />
  <meta itemprop="model" content="328i" />
  <div itemtype="https://schema.org/AutomotiveBusiness">
    <span itemprop="name"><strong>Pick-n-Pull Sacramento</strong></span>
  </div>
  <p itemprop="address">Sacramento, CA</p>
  <a itemprop="url" href="/Vehicle/Detail/12345">View</a>
  <div class="col-md-1"><strong>Jan 15, 2025</strong></div>
</div>
<div class="list-row">
  <meta itemprop="year" content="2014" />
  <meta itemprop="make" content="BMW" />
  <meta itemprop="model" content="535i" />
  <div itemtype="https://schema.org/AutomotiveBusiness">
    <span itemprop="name"><strong>LKQ Portland</strong></span>
  </div>
  <p itemprop="address">Portland, OR</p>
  <a itemprop="url" href="/Vehicle/Detail/67890">View</a>
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

FCPEURO_GTM_HTML = """
<html><body>
<turbo-frame id="product-results" data-gtm-event-event-value='{"ecommerce":{"items":[{"item_id":"34116799166","item_name":"Genuine BMW Brake Pad Set - Front","item_brand":"Genuine BMW","price":"79.99"},{"item_id":"34116855000","item_name":"ATE Brake Rotor Front","item_brand":"ATE","price":"124.95"}]}}'>
  <div class="hit">
    <a class="hit__name" href="/brake-pad-set-genuine-bmw">Genuine BMW Brake Pad Set - Front</a>
    <span class="hit__money">$79.99</span>
    <img src="https://media.fcpeuro.com/brake-pad.jpg" />
  </div>
  <div class="hit">
    <a class="hit__name" href="/brake-rotor-ate">ATE Brake Rotor Front</a>
    <span class="hit__money">$124.95</span>
    <img src="https://media.fcpeuro.com/rotor.jpg" />
  </div>
</turbo-frame>
</body></html>
"""

FCPEURO_HITCARD_HTML = """
<html><body>
<div class="hit">
  <a class="hit__name" href="/brake-pad-set-genuine-bmw">Genuine BMW Brake Pad Set - Front</a>
  <span class="hit__money">$79.99</span>
  <span class="hit__flag">OE</span>
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

ROCKAUTO_HTML = """
<html><body>
<table>
<tbody class="listing-inner">
  <span class="listing-final-manufacturer">Bosch</span>
  <span class="listing-final-partnumber">BC905</span>
  <span class="listing-footnote-text">QuietCast Premium Ceramic Disc Brake Pad Set</span>
  <span class="listing-price">$32.79</span>
  <img src="https://www.rockauto.com/images/brake.jpg" />
</tbody>
<tbody class="listing-inner">
  <span class="listing-final-manufacturer">Wagner</span>
  <span class="listing-final-partnumber">ZD1375</span>
  <span class="listing-footnote-text">ThermoQuiet Ceramic Disc Brake Pad Set</span>
  <span class="listing-price">$28.49</span>
</tbody>
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


# --- Helper to mock fetch_html ---

def _mock_fetch(html_content):
    """Return an AsyncMock that resolves to (html, 200)."""
    return AsyncMock(return_value=(html_content, 200))


def _mock_fetch_error():
    """Return an AsyncMock that raises an exception."""
    return AsyncMock(side_effect=Exception("Connection refused"))


def _make_mock_page(html_content):
    """Create a mock Playwright page that returns the given HTML."""
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.content = AsyncMock(return_value=html_content)
    mock_page.close = AsyncMock()
    return mock_page


def _make_mock_get_page(html_content):
    """Create a mock get_page context manager returning a page with given HTML."""
    mock_page = _make_mock_page(html_content)

    @asynccontextmanager
    async def mock_get_page(**kwargs):
        yield mock_page

    return mock_get_page


# --- CarPart tests (link generator only — no free-text search URL) ---

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
        assert "2012" in hit.vehicle
        assert "BMW" in hit.vehicle
        assert "328i" in hit.vehicle
        assert hit.yard_name == "Pick-n-Pull Sacramento"
        assert hit.yard_location == "Sacramento, CA"
        assert hit.url == "https://row52.com/Vehicle/Detail/12345"

    @pytest.mark.asyncio
    async def test_scrape_parses_date(self):
        from app.ingestion.row52 import Row52Connector
        connector = Row52Connector()
        with patch("app.ingestion.row52.fetch_html", _mock_fetch(ROW52_HTML)), \
             patch("app.ingestion.row52.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.carpart_default_zip = ""
            mock_settings.max_results_per_source = 20
            result = await connector.search("BMW")

        hit = result["salvage_hits"][0]
        assert hit.last_seen == "Jan 15, 2025"
        # Second hit has no date
        hit2 = result["salvage_hits"][1]
        assert hit2.last_seen is None

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

    @pytest.mark.asyncio
    async def test_link_mode_when_scrape_disabled(self):
        from app.ingestion.row52 import Row52Connector
        connector = Row52Connector()
        with patch("app.ingestion.row52.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.carpart_default_zip = ""
            result = await connector.search("BMW brake")

        assert len(result["external_links"]) >= 1
        assert result["salvage_hits"] == []


# --- ECS Tuning tests (Playwright-based) ---

class TestECSTuningConnector:
    @pytest.mark.asyncio
    async def test_scrape_parses_listings(self):
        from app.ingestion.ecstuning import ECSTuningConnector
        connector = ECSTuningConnector()
        mock_get_page = _make_mock_get_page(ECSTUNING_HTML)

        with patch("app.ingestion.ecstuning.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = True
            mock_settings.max_results_per_source = 20
            with patch("app.utils.browser.get_page", mock_get_page):
                import app.utils.browser
                with patch.object(app.utils.browser, "get_page", mock_get_page):
                    result = await connector._scrape("BMW brake pad")

        assert result["error"] is None
        assert len(result["market_listings"]) == 2
        listing = result["market_listings"][0]
        assert listing.source == "ecstuning"
        assert listing.price == 89.99
        assert listing.condition == "New"
        assert listing.brand == "BMW"

    @pytest.mark.asyncio
    async def test_fallback_when_playwright_disabled(self):
        from app.ingestion.ecstuning import ECSTuningConnector
        connector = ECSTuningConnector()
        with patch("app.ingestion.ecstuning.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []

    @pytest.mark.asyncio
    async def test_fallback_when_scrape_disabled(self):
        from app.ingestion.ecstuning import ECSTuningConnector
        connector = ECSTuningConnector()
        with patch("app.ingestion.ecstuning.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = True
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []


# --- FCP Euro tests ---

class TestFCPEuroConnector:
    @pytest.mark.asyncio
    async def test_scrape_gtm_json(self):
        """Test parsing GTM JSON embedded in turbo-frame."""
        from app.ingestion.fcpeuro import FCPEuroConnector
        connector = FCPEuroConnector()
        with patch("app.ingestion.fcpeuro.fetch_html", _mock_fetch(FCPEURO_GTM_HTML)), \
             patch("app.ingestion.fcpeuro.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("BMW brake pad")

        assert result["error"] is None
        assert len(result["market_listings"]) == 2
        listing = result["market_listings"][0]
        assert listing.source == "fcpeuro"
        assert listing.price == 79.99
        assert listing.brand == "Genuine BMW"
        assert listing.title == "Genuine BMW Brake Pad Set - Front"
        # GTM enrichment should add image from .hit card
        assert listing.image_url == "https://media.fcpeuro.com/brake-pad.jpg"
        # Product URL from .hit card link
        assert "brake-pad-set-genuine-bmw" in listing.url

    @pytest.mark.asyncio
    async def test_scrape_hit_cards_fallback(self):
        """Test parsing .hit cards when GTM JSON is unavailable."""
        from app.ingestion.fcpeuro import FCPEuroConnector
        connector = FCPEuroConnector()
        with patch("app.ingestion.fcpeuro.fetch_html", _mock_fetch(FCPEURO_HITCARD_HTML)), \
             patch("app.ingestion.fcpeuro.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("BMW brake pad")

        assert result["error"] is None
        assert len(result["market_listings"]) == 1
        listing = result["market_listings"][0]
        assert listing.source == "fcpeuro"
        assert listing.price == 79.99
        assert listing.brand == "OE"
        assert "brake-pad-set-genuine-bmw" in listing.url

    @pytest.mark.asyncio
    async def test_fallback_on_scrape_failure(self):
        from app.ingestion.fcpeuro import FCPEuroConnector
        connector = FCPEuroConnector()
        with patch("app.ingestion.fcpeuro.fetch_html", _mock_fetch_error()), \
             patch("app.ingestion.fcpeuro.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.max_results_per_source = 20
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []

    @pytest.mark.asyncio
    async def test_link_mode_when_scrape_disabled(self):
        from app.ingestion.fcpeuro import FCPEuroConnector
        connector = FCPEuroConnector()
        with patch("app.ingestion.fcpeuro.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []


# --- Partsouq tests (Playwright-based) ---

class TestPartsouqConnector:
    @pytest.mark.asyncio
    async def test_scrape_parses_listings(self):
        from app.ingestion.partsouq import PartsouqConnector
        connector = PartsouqConnector()
        mock_get_page = _make_mock_get_page(PARTSOUQ_HTML)

        with patch("app.ingestion.partsouq.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = True
            mock_settings.max_results_per_source = 20
            with patch("app.utils.browser.get_page", mock_get_page):
                import app.utils.browser
                with patch.object(app.utils.browser, "get_page", mock_get_page):
                    result = await connector._scrape("34-11-6-799-166")

        assert result["error"] is None
        assert len(result["market_listings"]) == 1
        listing = result["market_listings"][0]
        assert listing.source == "partsouq"
        assert listing.price == 65.0
        assert "34-11-6-799-166" in listing.part_numbers

    @pytest.mark.asyncio
    async def test_fallback_when_playwright_disabled(self):
        from app.ingestion.partsouq import PartsouqConnector
        connector = PartsouqConnector()
        with patch("app.ingestion.partsouq.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = False
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []

    @pytest.mark.asyncio
    async def test_fallback_when_scrape_disabled(self):
        from app.ingestion.partsouq import PartsouqConnector
        connector = PartsouqConnector()
        with patch("app.ingestion.partsouq.settings") as mock_settings:
            mock_settings.scrape_enabled = False
            mock_settings.playwright_enabled = True
            result = await connector.search("brake pad")

        assert len(result["external_links"]) >= 1
        assert result["market_listings"] == []


# --- RockAuto tests (Playwright-based) ---

class TestRockAutoConnector:
    @pytest.mark.asyncio
    async def test_scrape_parses_listings(self):
        from app.ingestion.rockauto import RockAutoConnector
        connector = RockAutoConnector()
        mock_get_page = _make_mock_get_page(ROCKAUTO_HTML)

        with patch("app.ingestion.rockauto.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = True
            mock_settings.max_results_per_source = 20
            with patch("app.utils.browser.get_page", mock_get_page):
                import app.utils.browser
                with patch.object(app.utils.browser, "get_page", mock_get_page):
                    result = await connector._scrape("brake pads")

        assert result["error"] is None
        assert len(result["market_listings"]) == 2
        listing = result["market_listings"][0]
        assert listing.source == "rockauto"
        assert listing.price == 32.79
        assert listing.brand == "Bosch"
        assert "BC905" in listing.part_numbers

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


# --- PartsGeek tests ---

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


# --- Amazon tests ---

class TestAmazonConnector:
    @pytest.mark.asyncio
    async def test_scrape_parses_listings(self):
        from app.ingestion.amazon import AmazonConnector
        connector = AmazonConnector()
        mock_get_page = _make_mock_get_page(AMAZON_HTML)

        with patch("app.ingestion.amazon.settings") as mock_settings:
            mock_settings.scrape_enabled = True
            mock_settings.playwright_enabled = True
            mock_settings.max_results_per_source = 20
            with patch("app.utils.browser.get_page", mock_get_page):
                import app.utils.browser
                with patch.object(app.utils.browser, "get_page", mock_get_page):
                    result = await connector._scrape("brake pads")

        assert result["error"] is None
        assert len(result["market_listings"]) == 1
        listing = result["market_listings"][0]
        assert listing.source == "amazon"
        assert listing.price == 24.97
        assert "Bosch" in listing.title

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
