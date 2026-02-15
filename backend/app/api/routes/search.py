"""
Search API route - main endpoint for part searches.
Uses connector registry and parallel execution.
"""

import asyncio
import json
import logging
import time
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, Query

from app.config import settings
from app.data.source_registry import get_active_sources as get_registry_sources
from app.db import record_price_snapshots_bulk, record_search
from app.ingestion import get_all_connectors, get_connector
from app.ingestion.base import BaseConnector
from app.schemas.search import (
    BrandSummary,
    ExternalLink,
    InterchangeInfo,
    ListingGroup,
    MarketListing,
    Offer,
    PartIntelligence,
    SalvageHit,
    SearchResponse,
    SearchResults,
    SourceStatus,
)
from app.utils.brand_intelligence import build_brand_comparison
from app.utils.cross_reference import enrich_with_cross_references
from app.utils.deduplication import deduplicate_links, deduplicate_listings
from app.utils.grouping import group_listings, sort_groups
from app.utils.interchange import InterchangeGroup, build_interchange_group
from app.utils.part_numbers import extract_part_numbers, normalize_query
from app.utils.query_analysis import QueryType, analyze_query
from app.utils.ranking import filter_salvage_hits, group_links_by_category, rank_listings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def _get_connector_routing():
    """
    Build connector routing sets from the source registry.

    Sources with supports_part_number_search=True go into PART_NUMBER_SOURCES.
    Sources in used_aggregator/salvage_yard categories go into VEHICLE_SOURCES.
    The 'resources' connector always runs.

    Falls back to hardcoded defaults if registry is empty.
    """
    # Map registry domains to connector source_names
    # (connector names are short identifiers; registry uses full domains)
    _DOMAIN_TO_CONNECTOR = {
        "ebay.com": "ebay",
        "rockauto.com": "rockauto",
        "row52.com": "row52",
        "car-part.com": "carpart",
        "partsouq.com": "partsouq",
        "ecstuning.com": "ecstuning",
        "fcpeuro.com": "fcpeuro",
        "amazon.com": "amazon",
        "partsgeek.com": "partsgeek",
        "autozone.com": "autozone",
        "oreillyauto.com": "oreilly",
        "napaonline.com": "napa",
        "lkqonline.com": "lkq",
        "advanceautoparts.com": "advanceauto",
        "carparts.com": "carpartsdotcom",
    }

    try:
        registry_sources = get_registry_sources()
    except Exception:
        # Fallback if registry unavailable
        return (
            {"ebay", "rockauto", "partsouq", "ecstuning", "fcpeuro", "partsgeek", "amazon"},
            {"row52", "carpart"},
            {"resources"},
        )

    pn_sources = set()
    vehicle_sources = set()
    always_sources = {"resources"}

    for src in registry_sources:
        domain = src["domain"]
        connector_name = _DOMAIN_TO_CONNECTOR.get(domain)
        if not connector_name:
            continue  # No connector implementation for this domain yet

        # Only route to connectors that actually exist
        if not get_connector(connector_name):
            continue

        category = src.get("category", "")

        if category in ("used_aggregator", "salvage_yard"):
            vehicle_sources.add(connector_name)
        elif src.get("supports_part_number_search", True):
            pn_sources.add(connector_name)

    # Ensure we always have at least the core connectors
    if not pn_sources:
        pn_sources = {"ebay", "rockauto", "partsouq", "ecstuning", "fcpeuro", "partsgeek", "amazon"}
    if not vehicle_sources:
        vehicle_sources = {"row52", "carpart"}

    return pn_sources, vehicle_sources, always_sources


# Redis client (will be initialized in startup)
redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = await redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
        )
    return redis_client


async def get_cached_result(cache_key: str) -> dict | None:
    """Get cached result from Redis."""
    try:
        client = await get_redis_client()
        cached = await client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis cache read error: {e}")
    return None


async def set_cached_result(cache_key: str, result: dict, ttl: int | None = None):
    """Cache result in Redis."""
    try:
        client = await get_redis_client()
        await client.setex(cache_key, ttl or settings.cache_ttl_seconds, json.dumps(result))
    except Exception as e:
        logger.warning(f"Redis cache write error: {e}")


async def _run_connector(
    connector: BaseConnector,
    query: str,
    extra_kwargs: dict[str, Any],
    matched_interchange: str | None = None,
) -> dict[str, Any]:
    """Run a single connector with per-source caching, timeout, and error handling."""
    source_name = connector.source_name

    # Check source-specific cache first
    cache_key = connector.get_cache_key(query)
    cached = await get_cached_result(cache_key)
    if cached:
        logger.info(f"Serving cached {source_name} result")
        return {**cached, "_status": "cached", "_source": source_name, "_matched_interchange": matched_interchange}

    try:
        result = await asyncio.wait_for(
            connector.search(query, **extra_kwargs),
            timeout=settings.connector_timeout,
        )
        # Cache the result
        await set_cached_result(cache_key, result)
        result["_status"] = "ok" if not result.get("error") else "error"
        result["_source"] = source_name
        result["_matched_interchange"] = matched_interchange
        return result

    except TimeoutError:
        logger.error(f"{source_name} timed out after {settings.connector_timeout}s")
        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": [],
            "error": f"Timed out after {settings.connector_timeout}s",
            "_status": "error",
            "_source": source_name,
            "_matched_interchange": matched_interchange,
        }
    except Exception as e:
        logger.error(f"Error querying {source_name}: {e}")
        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": [],
            "error": str(e),
            "_status": "error",
            "_source": source_name,
            "_matched_interchange": matched_interchange,
        }


def _build_interchange_info(group: InterchangeGroup) -> InterchangeInfo:
    """Convert an InterchangeGroup dataclass to an InterchangeInfo schema."""
    return InterchangeInfo(
        primary_part_number=group.primary_part_number,
        interchange_numbers=group.interchange_numbers,
        brands_by_number=group.brands,
        confidence=group.confidence,
        sources_consulted=group.sources_consulted,
    )


@router.get("", response_model=SearchResponse)
async def search_parts(
    query: str = Query(..., description="Search query (part number, keywords, etc.)"),
    zip_code: str | None = Query(None, description="Zip code for location-based searches"),
    max_results: int = Query(20, ge=1, le=50, description="Max results per source"),
    sort: str = Query("relevance", description="Sort order: relevance, price_asc, price_desc, value"),
):
    """
    Search for parts across multiple sources in parallel.

    Sources include eBay (API when configured), RockAuto, Row52, Car-Part.com,
    Partsouq, ECS Tuning, FCP Euro, Amazon Automotive, PartsGeek,
    and repair resources (YouTube, Charm.li).

    Results are cached for 6 hours per (source, query) combination.
    Smart routing skips irrelevant sources based on query type.
    """
    search_start = time.monotonic()
    normalized_query = normalize_query(query)
    extracted_part_numbers = extract_part_numbers(normalized_query)

    # Check for cached overall result first
    overall_cache_key = f"search:overall:{normalized_query}:{sort}"
    cached_overall = await get_cached_result(overall_cache_key)

    if cached_overall:
        logger.info(f"Serving cached result for query: {normalized_query}")
        response = SearchResponse(**cached_overall)
        response.cached = True
        return response

    # --- Query Analysis ---
    analysis = analyze_query(normalized_query)

    # --- Interchange Expansion (Phase 5) ---
    interchange_group: InterchangeGroup | None = None

    if analysis.query_type == QueryType.PART_NUMBER and settings.scrape_enabled:
        if settings.interchange_enabled:
            # Full interchange expansion: fans out to multiple providers
            try:
                interchange_group = await build_interchange_group(analysis)
                if interchange_group:
                    logger.info(
                        f"Interchange expansion: {len(interchange_group.interchange_numbers)} "
                        f"interchange PNs from {len(interchange_group.sources_consulted)} sources"
                    )
            except Exception as e:
                logger.warning(f"Interchange expansion failed: {e}")
        else:
            # Legacy: single-source FCP Euro enrichment
            try:
                analysis = await enrich_with_cross_references(analysis)
                logger.info(
                    f"Cross-ref enrichment: vehicle={analysis.vehicle_hint}, "
                    f"part={analysis.part_description}, "
                    f"xrefs={len(analysis.cross_references)}, "
                    f"brands={len(analysis.brands_found)}"
                )
            except Exception as e:
                logger.warning(f"Cross-reference enrichment failed: {e}")

    # --- Smart Connector Routing (registry-driven) ---
    PART_NUMBER_SOURCES, VEHICLE_SOURCES, ALWAYS_SOURCES = _get_connector_routing()
    connectors = get_all_connectors()
    shared_kwargs: dict[str, Any] = {
        "max_results": max_results,
        "zip_code": zip_code,
        "part_numbers": extracted_part_numbers + analysis.cross_references,
    }

    tasks = []

    if analysis.query_type == QueryType.PART_NUMBER:
        # Part number query: send to part-number-capable sources
        active_sources = PART_NUMBER_SOURCES | ALWAYS_SOURCES
        for connector in connectors:
            if connector.source_name in active_sources:
                tasks.append(_run_connector(connector, normalized_query, shared_kwargs))

        # If cross-ref found vehicle context, also query vehicle sources
        # with the vehicle description instead of the raw part number
        if analysis.vehicle_hint and analysis.part_description:
            vehicle_query = f"{analysis.vehicle_hint} {analysis.part_description}".upper()
            vehicle_kwargs = {**shared_kwargs, "part_numbers": extracted_part_numbers}
            for connector in connectors:
                if connector.source_name in VEHICLE_SOURCES:
                    tasks.append(_run_connector(connector, vehicle_query, vehicle_kwargs))
        else:
            # Skip vehicle sources entirely for part number queries without context
            for connector in connectors:
                if connector.source_name in VEHICLE_SOURCES:
                    logger.info(f"Skipping {connector.source_name} for part number query (no vehicle context)")

        # --- Interchange searches: search top interchange PNs across connectors ---
        if interchange_group and interchange_group.interchange_numbers:
            interchange_pns = interchange_group.interchange_numbers[: settings.max_interchange_searches]
            # Pick a subset of connectors for interchange searches (avoid overwhelming)
            interchange_sources = {"ebay", "rockauto", "partsgeek"}
            for pn in interchange_pns:
                for connector in connectors:
                    if connector.source_name in interchange_sources:
                        ic_kwargs = {**shared_kwargs, "part_numbers": [pn]}
                        tasks.append(_run_connector(connector, pn, ic_kwargs, matched_interchange=pn))
    else:
        # Vehicle+part or keyword queries: search all sources as before
        for connector in connectors:
            tasks.append(_run_connector(connector, normalized_query, shared_kwargs))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results
    market_listings: list[MarketListing] = []
    salvage_hits: list[SalvageHit] = []
    external_links: list[ExternalLink] = []
    sources_queried: list[SourceStatus] = []
    warnings: list[str] = []

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Connector raised exception: {result}")
            continue

        source_name = result.get("_source", "unknown")
        status = result.get("_status", "error")
        error_msg = result.get("error")
        matched_ic = result.get("_matched_interchange")

        # Parse raw dicts back into models if they came from cache
        for item in result.get("market_listings", []):
            if isinstance(item, dict):
                listing = MarketListing(**item)
            else:
                listing = item
            # Tag with interchange PN if this was an interchange search
            if matched_ic and not listing.matched_interchange:
                listing.matched_interchange = matched_ic
            market_listings.append(listing)

        for item in result.get("salvage_hits", []):
            if isinstance(item, dict):
                salvage_hits.append(SalvageHit(**item))
            else:
                salvage_hits.append(item)

        for item in result.get("external_links", []):
            if isinstance(item, dict):
                external_links.append(ExternalLink(**item))
            else:
                external_links.append(item)

        result_count = (
            len(result.get("market_listings", []))
            + len(result.get("salvage_hits", []))
            + len(result.get("external_links", []))
        )
        sources_queried.append(
            SourceStatus(
                source=source_name,
                status=status,
                details=error_msg or "Success",
                result_count=result_count,
            )
        )

        if error_msg:
            warnings.append(f"{source_name}: {error_msg}")

    # Deduplication
    market_listings = deduplicate_listings(market_listings)
    external_links = deduplicate_links(external_links)

    # Relevance filtering: remove irrelevant salvage hits
    salvage_hits = filter_salvage_hits(salvage_hits, analysis)

    # Ranking / sorting (context-aware)
    market_listings = rank_listings(market_listings, normalized_query, sort, analysis)
    external_links = group_links_by_category(external_links)

    # --- Brand Intelligence ---
    brand_comparison: list[BrandSummary] = []
    if market_listings:
        brand_comparison = build_brand_comparison(
            market_listings,
            interchange=interchange_group,
            analysis=analysis,
        )

    # --- Listing Grouping (price comparison across retailers) ---
    raw_groups = group_listings(market_listings)
    # Sort groups based on user preference
    group_sort = "value" if sort == "value" else sort
    sorted_groups = sort_groups(raw_groups, group_sort)
    grouped_listings = [
        ListingGroup(
            brand=g["brand"],
            part_number=g["part_number"],
            tier=g["tier"],
            quality_score=g["quality_score"],
            offers=[Offer(**o) for o in g["offers"]],
            best_price=g["best_price"],
            price_range=g["price_range"],
            offer_count=g["offer_count"],
            best_value_score=g["best_value_score"],
        )
        for g in sorted_groups
    ]

    # Build intelligence data for the response
    intelligence = PartIntelligence(
        query_type=analysis.query_type.value,
        vehicle_hint=analysis.vehicle_hint,
        part_description=analysis.part_description,
        cross_references=analysis.cross_references,
        brands_found=analysis.brands_found,
        interchange=_build_interchange_info(interchange_group) if interchange_group else None,
        brand_comparison=brand_comparison,
    )

    # Build response
    search_results = SearchResults(
        market_listings=market_listings,
        salvage_hits=salvage_hits,
        external_links=external_links,
    )
    response_data = {
        "query": normalized_query,
        "extracted_part_numbers": extracted_part_numbers,
        "results": search_results.model_dump(),
        "grouped_listings": [g.model_dump() for g in grouped_listings],
        "sources_queried": [s.model_dump() for s in sources_queried],
        "warnings": warnings,
        "cached": False,
        "intelligence": intelligence.model_dump(),
    }

    # Cache overall result
    await set_cached_result(overall_cache_key, response_data)

    # --- Record to SQLite (async, non-blocking) ---
    response_time_ms = int((time.monotonic() - search_start) * 1000)
    try:
        await record_search(
            query=query,
            normalized_query=normalized_query,
            query_type=analysis.query_type.value,
            vehicle_hint=analysis.vehicle_hint,
            part_description=analysis.part_description,
            sort=sort,
            market_listing_count=len(market_listings),
            salvage_hit_count=len(salvage_hits),
            external_link_count=len(external_links),
            source_count=len(sources_queried),
            has_interchange=interchange_group is not None,
            cached=False,
            response_time_ms=response_time_ms,
        )
        # Record price snapshots for all market listings
        if market_listings:
            snapshots = [
                {
                    "query": normalized_query,
                    "source": ml.source,
                    "part_number": ml.part_numbers[0] if ml.part_numbers else None,
                    "brand": ml.brand,
                    "title": ml.title,
                    "price": ml.price,
                    "shipping_cost": ml.shipping_cost or 0,
                    "condition": ml.condition,
                    "url": ml.url,
                }
                for ml in market_listings
            ]
            await record_price_snapshots_bulk(snapshots)
    except Exception as e:
        logger.warning(f"Failed to record search to DB: {e}")

    return SearchResponse(**response_data)
