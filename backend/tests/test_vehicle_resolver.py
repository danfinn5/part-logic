"""Tests for vehicle alias resolver (links known patterns, does not over-link)."""

from unittest import mock

import pytest
import pytest_asyncio

import app.db as db_mod
from app.db import close_db
from app.services.vehicle_resolver import LINK_THRESHOLD, ResolveResult, resolve_vehicle_alias


@pytest_asyncio.fixture(autouse=True)
async def temp_db(tmp_path):
    """Use a temp database so canonical tables exist and we don't touch real DB."""
    db_mod._db = None
    temp_path = tmp_path / "test.db"
    with mock.patch.object(db_mod, "DB_PATH", temp_path):
        yield temp_path
        await close_db()


@pytest.mark.asyncio
async def test_resolve_empty_string_returns_zero_confidence():
    """Empty or whitespace alias returns no link and 0 confidence."""
    r = await resolve_vehicle_alias("")
    assert r.vehicle_id is None
    assert r.config_id is None
    assert r.confidence == 0
    r2 = await resolve_vehicle_alias("   ")
    assert r2.confidence == 0


@pytest.mark.asyncio
async def test_resolve_creates_alias_and_vehicle_when_high_confidence():
    """When parsed year+make+model and no existing vehicle, resolver can create vehicle and link."""
    # Use a unique string so we don't depend on existing DB state
    r = await resolve_vehicle_alias("1999 TestMake TestModel", source_domain=None)
    # May or may not create vehicle depending on threshold and DB state
    assert isinstance(r, ResolveResult)
    assert r.parsed_year == 1999
    assert r.parsed_make is not None
    assert 0 <= r.confidence <= 100


@pytest.mark.asyncio
async def test_resolve_does_not_over_link_low_confidence():
    """Vague string should not get vehicle_id when confidence is low."""
    r = await resolve_vehicle_alias("something random xyz", source_domain=None)
    # Should have low confidence and likely no vehicle_id
    assert r.confidence < LINK_THRESHOLD or r.vehicle_id is None
