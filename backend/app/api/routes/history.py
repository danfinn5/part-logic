"""
Search history and price tracking API endpoints.

Provides access to search history, price trends, and statistics
from the SQLite database.
"""

from fastapi import APIRouter, Query

from app.db import (
    get_popular_searches,
    get_price_history,
    get_price_trends,
    get_recent_searches,
    get_search_stats,
)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/searches")
async def recent_searches(limit: int = Query(20, ge=1, le=100)):
    """Get recent search history."""
    searches = await get_recent_searches(limit)
    return {"searches": searches, "count": len(searches)}


@router.get("/searches/popular")
async def popular_searches(
    limit: int = Query(20, ge=1, le=100),
    days: int = Query(7, ge=1, le=365),
):
    """Get most popular searches in the last N days."""
    searches = await get_popular_searches(limit, days)
    return {"searches": searches, "count": len(searches)}


@router.get("/searches/stats")
async def search_statistics():
    """Get overall search statistics."""
    return await get_search_stats()


@router.get("/prices")
async def price_history(
    part_number: str | None = Query(None, description="Filter by part number"),
    brand: str | None = Query(None, description="Filter by brand"),
    source: str | None = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
):
    """Get price history for a part, optionally filtered."""
    prices = await get_price_history(part_number, brand, source, limit)
    return {"prices": prices, "count": len(prices)}


@router.get("/prices/trends")
async def price_trends(
    part_number: str = Query(..., description="Part number to track"),
    days: int = Query(30, ge=1, le=365),
):
    """Get price trends (daily averages) for a specific part number."""
    trends = await get_price_trends(part_number, days)
    return {"trends": trends, "part_number": part_number, "days": days}
