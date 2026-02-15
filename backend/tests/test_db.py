"""Tests for the SQLite database layer."""

from unittest import mock

import pytest
import pytest_asyncio

import app.db as db_mod
from app.db import (
    close_db,
    get_popular_searches,
    get_price_history,
    get_recent_searches,
    get_search_stats,
    record_price_snapshot,
    record_price_snapshots_bulk,
    record_search,
)


@pytest_asyncio.fixture(autouse=True)
async def temp_db(tmp_path):
    """Use a temp database for each test."""
    db_mod._db = None
    temp_path = tmp_path / "test.db"
    with mock.patch.object(db_mod, "DB_PATH", temp_path):
        yield temp_path
        await close_db()


class TestSearchHistory:
    @pytest.mark.asyncio
    async def test_record_and_retrieve(self):
        row_id = await record_search(
            query="brake pads",
            normalized_query="BRAKE PADS",
            query_type="keywords",
            market_listing_count=5,
            salvage_hit_count=2,
            source_count=8,
        )
        assert row_id > 0

        recent = await get_recent_searches(10)
        assert len(recent) == 1
        assert recent[0]["normalized_query"] == "BRAKE PADS"
        assert recent[0]["market_listing_count"] == 5

    @pytest.mark.asyncio
    async def test_multiple_searches(self):
        await record_search(query="q1", normalized_query="Q1")
        await record_search(query="q2", normalized_query="Q2")
        await record_search(query="q3", normalized_query="Q3")

        recent = await get_recent_searches(2)
        assert len(recent) == 2
        assert recent[0]["normalized_query"] == "Q3"  # most recent first

    @pytest.mark.asyncio
    async def test_search_stats(self):
        await record_search(
            query="test",
            normalized_query="TEST",
            query_type="part_number",
            market_listing_count=10,
            response_time_ms=500,
        )
        await record_search(
            query="test2",
            normalized_query="TEST2",
            query_type="keywords",
            market_listing_count=20,
            response_time_ms=1000,
        )

        stats = await get_search_stats()
        assert stats["total_searches"] == 2
        assert stats["unique_queries"] == 2
        assert stats["avg_listings_per_search"] == 15.0

    @pytest.mark.asyncio
    async def test_popular_searches(self):
        for _ in range(3):
            await record_search(query="popular", normalized_query="POPULAR")
        await record_search(query="rare", normalized_query="RARE")

        popular = await get_popular_searches(10, days=1)
        assert popular[0]["normalized_query"] == "POPULAR"
        assert popular[0]["count"] == 3


class TestPriceSnapshots:
    @pytest.mark.asyncio
    async def test_record_single_price(self):
        row_id = await record_price_snapshot(
            query="brake pads",
            source="rockauto",
            title="Ceramic Brake Pads",
            price=29.99,
            part_number="BP1234",
            brand="Bosch",
        )
        assert row_id > 0

        history = await get_price_history(part_number="BP1234")
        assert len(history) == 1
        assert history[0]["price"] == 29.99
        assert history[0]["brand"] == "Bosch"

    @pytest.mark.asyncio
    async def test_zero_price_skipped(self):
        row_id = await record_price_snapshot(
            query="test",
            source="test",
            title="Free",
            price=0.0,
        )
        assert row_id == 0

    @pytest.mark.asyncio
    async def test_bulk_recording(self):
        snapshots = [
            {"query": "q", "source": "s1", "title": "T1", "price": 10.0, "part_number": "PN1"},
            {"query": "q", "source": "s2", "title": "T2", "price": 20.0, "part_number": "PN1"},
            {"query": "q", "source": "s3", "title": "T3", "price": 0.0, "part_number": "PN1"},
        ]
        count = await record_price_snapshots_bulk(snapshots)
        assert count == 2  # zero-price excluded

        history = await get_price_history(part_number="PN1")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_filter_by_source(self):
        await record_price_snapshot(
            query="q",
            source="rockauto",
            title="T1",
            price=10.0,
            part_number="PN1",
        )
        await record_price_snapshot(
            query="q",
            source="fcpeuro",
            title="T2",
            price=20.0,
            part_number="PN1",
        )

        ra_only = await get_price_history(source="rockauto")
        assert len(ra_only) == 1
        assert ra_only[0]["source"] == "rockauto"
