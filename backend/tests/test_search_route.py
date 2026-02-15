"""Tests for the search API endpoint."""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.schemas.search import ExternalLink


@pytest.fixture
def mock_redis():
    """Mock Redis and cross-reference enrichment."""
    with patch("app.api.routes.search.get_cached_result", new_callable=AsyncMock, return_value=None), \
         patch("app.api.routes.search.set_cached_result", new_callable=AsyncMock), \
         patch("app.api.routes.search.enrich_with_cross_references", new_callable=AsyncMock, side_effect=lambda a: a):
        yield


@pytest.mark.asyncio
async def test_search_returns_200(mock_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "brake pads"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_response_structure(mock_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "brake pads"})
    data = response.json()

    assert "query" in data
    assert "extracted_part_numbers" in data
    assert "results" in data
    assert "market_listings" in data["results"]
    assert "salvage_hits" in data["results"]
    assert "external_links" in data["results"]
    assert "sources_queried" in data
    assert "warnings" in data
    assert "intelligence" in data


@pytest.mark.asyncio
async def test_search_returns_external_links(mock_redis):
    """Without eBay keys, all sources return external links."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "brake pads"})
    data = response.json()

    links = data["results"]["external_links"]
    assert len(links) > 0

    sources = {link["source"] for link in links}
    # Should have links from multiple sources
    assert len(sources) >= 5


@pytest.mark.asyncio
async def test_search_queries_all_sources(mock_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "brake pads"})
    data = response.json()

    queried_sources = {s["source"] for s in data["sources_queried"]}
    expected = {"ebay", "rockauto", "row52", "carpart", "partsouq",
                "ecstuning", "fcpeuro", "amazon", "partsgeek", "resources"}
    assert queried_sources == expected


@pytest.mark.asyncio
async def test_search_with_sort_param(mock_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "brake pads", "sort": "price_asc"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_normalizes_query(mock_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "  brake  pads  "})
    data = response.json()
    assert data["query"] == "BRAKE PADS"


@pytest.mark.asyncio
async def test_search_extracts_part_numbers(mock_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "OEM 12345-ABC brake pads"})
    data = response.json()
    assert len(data["extracted_part_numbers"]) > 0


@pytest.mark.asyncio
async def test_search_includes_intelligence_field(mock_redis):
    """Intelligence field is present and reflects query type for keyword searches."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "brake pads"})
    data = response.json()

    assert "intelligence" in data
    intelligence = data["intelligence"]
    assert intelligence["query_type"] == "keywords"


@pytest.mark.asyncio
async def test_part_number_query_has_intelligence(mock_redis):
    """Part number queries produce intelligence with query_type 'part_number'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"query": "951-375-042-04"})
    data = response.json()

    assert "intelligence" in data
    intelligence = data["intelligence"]
    assert intelligence["query_type"] == "part_number"
