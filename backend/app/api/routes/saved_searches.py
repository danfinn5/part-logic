"""
Saved searches and price alerts API routes.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import (
    create_price_alert,
    delete_saved_search,
    get_pending_alerts,
    get_saved_searches,
    save_search,
)
from app.services.price_alert_checker import check_price_alerts
from app.utils.part_numbers import normalize_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/saved", tags=["saved"])


# ── Request Models ──────────────────────────────────────────────────


class SaveSearchRequest(BaseModel):
    query: str
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_year: str | None = None
    vin: str | None = None
    sort: str = "value"
    price_threshold: float | None = None


class CreateAlertRequest(BaseModel):
    saved_search_id: int
    target_price: float
    part_number: str | None = None
    brand: str | None = None


# ── Saved Searches ──────────────────────────────────────────────────


@router.post("/searches")
async def save_search_endpoint(req: SaveSearchRequest):
    """Save a search for later."""
    normalized = normalize_query(req.query)
    search_id = await save_search(
        query=req.query,
        normalized_query=normalized,
        vehicle_make=req.vehicle_make,
        vehicle_model=req.vehicle_model,
        vehicle_year=req.vehicle_year,
        vin=req.vin,
        sort=req.sort,
        price_threshold=req.price_threshold,
    )
    return {"id": search_id, "message": "Search saved"}


@router.get("/searches")
async def list_saved_searches():
    """List all active saved searches."""
    searches = await get_saved_searches(active_only=True)
    return {"searches": searches}


@router.delete("/searches/{search_id}")
async def delete_search(search_id: int):
    """Delete a saved search."""
    deleted = await delete_saved_search(search_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"message": "Search deleted"}


# ── Price Alerts ────────────────────────────────────────────────────


@router.post("/alerts")
async def create_alert(req: CreateAlertRequest):
    """Create a price alert for a saved search."""
    alert_id = await create_price_alert(
        saved_search_id=req.saved_search_id,
        target_price=req.target_price,
        part_number=req.part_number,
        brand=req.brand,
    )
    return {"id": alert_id, "message": "Alert created"}


@router.get("/alerts")
async def list_alerts():
    """List all pending (untriggered) price alerts."""
    alerts = await get_pending_alerts()
    return {"alerts": alerts}


@router.post("/alerts/check")
async def check_alerts():
    """Manually check all pending price alerts against recent price data."""
    triggered = await check_price_alerts()
    return {
        "checked": True,
        "triggered_count": len(triggered),
        "triggered": triggered,
    }
