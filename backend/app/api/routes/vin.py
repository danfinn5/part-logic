"""
VIN decoding API route.

Provides VIN → vehicle info lookup using NHTSA free API.
"""

import logging

from fastapi import APIRouter, Query

from app.services.vin_decoder import decode_vin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vin", tags=["vin"])


@router.get("/decode")
async def decode_vin_endpoint(
    vin: str = Query(..., description="17-character VIN to decode", min_length=17, max_length=17),
):
    """Decode a VIN to year/make/model/engine using NHTSA vPIC API (free, no auth)."""
    result = await decode_vin(vin)

    return {
        "vin": result.vin,
        "year": result.year,
        "make": result.make,
        "model": result.model,
        "trim": result.trim,
        "engine_displacement_l": result.engine_displacement_l,
        "engine_code": result.engine_code,
        "drive_type": result.drive_type,
        "body_class": result.body_class,
        "error": result.error,
    }
