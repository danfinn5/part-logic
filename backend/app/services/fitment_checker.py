"""
Fitment matching service.

Checks whether parts fit a user's specified vehicle by querying
the canonical fitment data in SQLite.
"""

import logging
from enum import Enum

from app.db_canonical import get_fitments_for_part_numbers

logger = logging.getLogger(__name__)


class FitmentStatus(str, Enum):
    CONFIRMED_FIT = "confirmed_fit"
    LIKELY_FIT = "likely_fit"
    UNKNOWN = "unknown"


async def check_fitments(
    part_numbers: list[str],
    vehicle_id: int | None,
) -> dict[str, str]:
    """
    Check fitments for part numbers against a vehicle.

    Returns dict of part_number -> FitmentStatus value.
    Only returns entries for parts that have known fitment.
    Never returns 'does_not_fit' — we default to unknown.
    """
    if not vehicle_id or not part_numbers:
        return {}

    try:
        return await get_fitments_for_part_numbers(part_numbers, vehicle_id)
    except Exception as e:
        logger.warning(f"Fitment check failed: {e}")
        return {}
