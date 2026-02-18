"""
VIN decoder using NHTSA vPIC API (free, no auth required).

Decodes a 17-character VIN to year/make/model/engine details.
Results are cached in Redis (30-day TTL) for fast repeat lookups.
"""

import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.IGNORECASE)

NHTSA_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"


@dataclass
class VINDecodeResult:
    vin: str
    year: int | None = None
    make: str | None = None
    model: str | None = None
    trim: str | None = None
    engine_displacement_l: float | None = None
    engine_code: str | None = None
    drive_type: str | None = None
    body_class: str | None = None
    error: str | None = None


def validate_vin(vin: str) -> str | None:
    """Validate a VIN string. Returns error message or None if valid."""
    if not vin or len(vin) != 17:
        return "VIN must be exactly 17 characters"
    if not _VIN_RE.match(vin):
        return "VIN contains invalid characters (I, O, Q not allowed)"
    return None


async def decode_vin(vin: str) -> VINDecodeResult:
    """Decode a VIN using NHTSA vPIC API."""
    vin = vin.upper().strip()

    # Validate
    error = validate_vin(vin)
    if error:
        return VINDecodeResult(vin=vin, error=error)

    # Check Redis cache
    cached = await _get_cached_vin(vin)
    if cached:
        return cached

    # Call NHTSA API
    try:
        url = NHTSA_API_URL.format(vin=vin)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.error(f"NHTSA API request failed for VIN {vin}: {e}")
        return VINDecodeResult(vin=vin, error=f"NHTSA API error: {e}")

    # Parse response
    results = data.get("Results", [])
    if not results:
        return VINDecodeResult(vin=vin, error="No results from NHTSA")

    r = results[0]

    # Check for decode errors
    error_code = r.get("ErrorCode", "")
    if error_code and error_code != "0" and "0" not in error_code.split(","):
        error_text = r.get("ErrorText", "Unknown decode error")
        # Some error codes are warnings, not failures — still return partial data
        logger.warning(f"NHTSA decode warning for {vin}: {error_text}")

    # Extract fields (NHTSA returns empty strings for missing values)
    def _clean(val: str | None) -> str | None:
        if not val or val.strip() == "" or val.strip().lower() == "not applicable":
            return None
        return val.strip()

    year_str = _clean(r.get("ModelYear"))
    displacement_str = _clean(r.get("DisplacementL"))

    result = VINDecodeResult(
        vin=vin,
        year=int(year_str) if year_str and year_str.isdigit() else None,
        make=_clean(r.get("Make")),
        model=_clean(r.get("Model")),
        trim=_clean(r.get("Trim")),
        engine_displacement_l=float(displacement_str) if displacement_str else None,
        engine_code=_clean(r.get("EngineModel")),
        drive_type=_clean(r.get("DriveType")),
        body_class=_clean(r.get("BodyClass")),
    )

    # Cache in Redis (30-day TTL)
    await _cache_vin(vin, result)

    return result


async def _get_cached_vin(vin: str) -> VINDecodeResult | None:
    """Check Redis cache for a decoded VIN."""
    try:
        from app.api.routes.search import get_cached_result

        data = await get_cached_result(f"vin:{vin}")
        if data:
            return VINDecodeResult(**data)
    except Exception:
        pass
    return None


async def _cache_vin(vin: str, result: VINDecodeResult):
    """Cache a decoded VIN in Redis (30-day TTL)."""
    try:
        from dataclasses import asdict

        from app.api.routes.search import set_cached_result

        await set_cached_result(f"vin:{vin}", asdict(result), ttl=30 * 86400)
    except Exception as e:
        logger.warning(f"Failed to cache VIN result: {e}")
