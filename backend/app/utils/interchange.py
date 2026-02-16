"""
Multi-source interchange part number expansion.

Fans out to multiple cross-reference providers in parallel to discover
all interchange/equivalent part numbers across brands for a given OEM number.
"""

import asyncio
import logging
from dataclasses import dataclass, field

from app.config import settings
from app.utils.cross_reference import (
    CrossRefResult,
    enrich_from_fcpeuro,
    enrich_from_parts_crossref,
    enrich_from_rockauto,
)
from app.utils.query_analysis import QueryAnalysis, QueryType

logger = logging.getLogger(__name__)


@dataclass
class InterchangeGroup:
    """A group of interchangeable part numbers across brands."""

    primary_part_number: str
    interchange_numbers: list[str] = field(default_factory=list)
    brands: dict[str, list[str]] = field(default_factory=dict)  # brand -> [part_numbers]
    vehicle_fitment: str | None = None
    part_description: str | None = None
    confidence: float = 0.0  # 0.0-1.0
    sources_consulted: list[str] = field(default_factory=list)


def _merge_cross_ref_results(
    primary_pn: str,
    results: list[CrossRefResult],
) -> InterchangeGroup:
    """Merge multiple CrossRefResult objects into a single InterchangeGroup."""
    group = InterchangeGroup(primary_part_number=primary_pn)

    all_part_numbers: set[str] = set()
    brands_map: dict[str, set[str]] = {}
    primary_upper = primary_pn.upper()

    for result in results:
        group.sources_consulted.append(result.source)

        # Collect part numbers (excluding primary)
        for pn in result.part_numbers:
            if pn.upper() != primary_upper:
                all_part_numbers.add(pn)

        # Collect brands and their part numbers
        for brand, pns in result.brands.items():
            if brand not in brands_map:
                brands_map[brand] = set()
            brands_map[brand].update(pns)

        # Take first non-None vehicle hint
        if not group.vehicle_fitment and result.vehicle_hint:
            group.vehicle_fitment = result.vehicle_hint

        # Take first non-None part description
        if not group.part_description and result.part_description:
            group.part_description = result.part_description

    group.interchange_numbers = sorted(all_part_numbers)
    group.brands = {k: sorted(v) for k, v in sorted(brands_map.items())}

    # Confidence: based on number of sources that returned data and agreement
    sources_with_data = sum(1 for r in results if r.part_numbers or r.brands)
    if sources_with_data >= 3:
        group.confidence = 0.9
    elif sources_with_data == 2:
        group.confidence = 0.7
    elif sources_with_data == 1:
        group.confidence = 0.5
    else:
        group.confidence = 0.0

    return group


async def build_interchange_group(analysis: QueryAnalysis) -> InterchangeGroup | None:
    """
    Fan out to multiple cross-reference providers in parallel,
    then merge and deduplicate results into an InterchangeGroup.

    Only runs for PART_NUMBER queries with interchange_enabled.
    Returns None if interchange is disabled or no part numbers found.
    """
    if not settings.interchange_enabled:
        return None

    if analysis.query_type != QueryType.PART_NUMBER:
        return None

    if not analysis.part_numbers:
        return None

    primary_pn = analysis.part_numbers[0]

    # Fan out to all providers in parallel
    providers = [
        enrich_from_fcpeuro(primary_pn),
        enrich_from_rockauto(primary_pn),
        enrich_from_parts_crossref(primary_pn),
    ]

    results: list[CrossRefResult] = []
    provider_results = await asyncio.gather(*providers, return_exceptions=True)

    for result in provider_results:
        if isinstance(result, Exception):
            logger.warning(f"Cross-ref provider failed: {result}")
            continue
        if result is not None:
            results.append(result)

    if not results:
        return None

    group = _merge_cross_ref_results(primary_pn, results)

    # Update analysis with merged data
    if group.vehicle_fitment and not analysis.vehicle_hint:
        analysis.vehicle_hint = group.vehicle_fitment
    if group.part_description and not analysis.part_description:
        analysis.part_description = group.part_description

    # Merge all interchange numbers into analysis cross_references
    existing_xrefs = {x.upper() for x in analysis.cross_references}
    for pn in group.interchange_numbers:
        if pn.upper() not in existing_xrefs:
            analysis.cross_references.append(pn)
    analysis.cross_references.sort()

    # Merge brands
    existing_brands = {b.upper() for b in analysis.brands_found}
    for brand in group.brands:
        if brand.upper() not in existing_brands:
            analysis.brands_found.append(brand)
    analysis.brands_found.sort()

    return group
