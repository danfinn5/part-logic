"""Tests for saved searches and price alerts."""

import pytest
import pytest_asyncio

from app.db import (
    close_db,
    create_price_alert,
    delete_saved_search,
    get_pending_alerts,
    get_saved_searches,
    record_price_snapshot,
    save_search,
    trigger_alert,
)
from app.services.price_alert_checker import check_price_alerts


@pytest_asyncio.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    """Use a temporary database for each test."""
    import app.db as db_module

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    monkeypatch.setattr(db_module, "_db", None)

    yield

    await close_db()


@pytest.mark.asyncio
async def test_save_and_get_search():
    """Test saving and retrieving a search."""
    sid = await save_search(
        query="BMW oil filter",
        normalized_query="BMW OIL FILTER",
        vehicle_make="BMW",
        vehicle_model="E46",
        vehicle_year="2003",
        sort="value",
    )
    assert sid > 0

    searches = await get_saved_searches()
    assert len(searches) == 1
    assert searches[0]["query"] == "BMW oil filter"
    assert searches[0]["vehicle_make"] == "BMW"


@pytest.mark.asyncio
async def test_delete_saved_search():
    """Test deleting a saved search."""
    sid = await save_search(
        query="brake pads",
        normalized_query="BRAKE PADS",
    )
    deleted = await delete_saved_search(sid)
    assert deleted is True

    searches = await get_saved_searches()
    assert len(searches) == 0

    # Deleting non-existent returns False
    deleted = await delete_saved_search(9999)
    assert deleted is False


@pytest.mark.asyncio
async def test_create_and_get_alerts():
    """Test creating and retrieving price alerts."""
    sid = await save_search(
        query="11427566327",
        normalized_query="11427566327",
    )
    alert_id = await create_price_alert(
        saved_search_id=sid,
        target_price=15.00,
        part_number="11427566327",
    )
    assert alert_id > 0

    alerts = await get_pending_alerts()
    assert len(alerts) == 1
    assert alerts[0]["target_price"] == 15.00
    assert alerts[0]["part_number"] == "11427566327"
    assert alerts[0]["triggered"] == 0


@pytest.mark.asyncio
async def test_trigger_alert():
    """Test triggering a price alert."""
    sid = await save_search(query="test", normalized_query="TEST")
    aid = await create_price_alert(saved_search_id=sid, target_price=20.00)

    triggered = await trigger_alert(
        aid,
        current_lowest=15.50,
        source="ebay",
        url="https://ebay.com/item/123",
    )
    assert triggered is True

    # Should no longer appear in pending
    pending = await get_pending_alerts()
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_check_price_alerts_triggers():
    """Test that alert checker finds matching price snapshots."""
    sid = await save_search(query="11427566327", normalized_query="11427566327")
    await create_price_alert(
        saved_search_id=sid,
        target_price=20.00,
        part_number="11427566327",
    )

    # Add a price snapshot below target
    await record_price_snapshot(
        query="11427566327",
        source="fcpeuro",
        title="Mann Oil Filter HU816X",
        price=12.99,
        part_number="11427566327",
    )

    triggered = await check_price_alerts()
    assert len(triggered) == 1
    assert triggered[0]["current_lowest"] == 12.99
    assert triggered[0]["source"] == "fcpeuro"


@pytest.mark.asyncio
async def test_check_price_alerts_no_trigger():
    """Alert should not trigger if price is above threshold."""
    sid = await save_search(query="expensive part", normalized_query="EXPENSIVE PART")
    await create_price_alert(
        saved_search_id=sid,
        target_price=5.00,
        part_number="EXPENSIVEPART",
    )

    await record_price_snapshot(
        query="EXPENSIVE PART",
        source="ebay",
        title="Expensive Part",
        price=50.00,
        part_number="EXPENSIVEPART",
    )

    triggered = await check_price_alerts()
    assert len(triggered) == 0
