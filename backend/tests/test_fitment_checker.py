"""Tests for fitment checker service."""

import pytest

from app.services.fitment_checker import check_fitments


@pytest.mark.asyncio
async def test_check_fitments_no_vehicle():
    """No vehicle ID should return empty dict."""
    result = await check_fitments(["11427566327"], None)
    assert result == {}


@pytest.mark.asyncio
async def test_check_fitments_no_parts():
    """No part numbers should return empty dict."""
    result = await check_fitments([], 1)
    assert result == {}


@pytest.mark.asyncio
async def test_check_fitments_with_data(monkeypatch):
    """Mock canonical DB to test fitment matching."""

    async def mock_get_fitments(part_numbers, vehicle_id):
        # Simulate: 11427566327 fits vehicle 1 with high confidence
        return {"11427566327": "confirmed_fit"}

    monkeypatch.setattr(
        "app.services.fitment_checker.get_fitments_for_part_numbers",
        mock_get_fitments,
    )

    result = await check_fitments(["11427566327", "UNKNOWN123"], 1)
    assert result == {"11427566327": "confirmed_fit"}
    assert "UNKNOWN123" not in result


@pytest.mark.asyncio
async def test_check_fitments_db_error(monkeypatch):
    """DB errors should return empty dict gracefully."""

    async def mock_error(part_numbers, vehicle_id):
        raise Exception("DB connection failed")

    monkeypatch.setattr(
        "app.services.fitment_checker.get_fitments_for_part_numbers",
        mock_error,
    )

    result = await check_fitments(["11427566327"], 1)
    assert result == {}
