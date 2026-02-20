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
    AIAnalysis,
    AIAvoidItem,
    AIRecommendation,
    BrandSummary,
    BuyLink,
    CommunitySource,
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
from app.services.ai_advisor import AIAdvisorResult, get_ai_recommendations
from app.services.community import CommunityThread, fetch_community_discussions
from app.services.fitment_checker import check_fitments
from app.services.vehicle_resolver import resolve_vehicle_alias
from app.utils.brand_intelligence import build_brand_comparison
from app.utils.cross_reference import enrich_with_cross_references
from app.utils.deduplication import deduplicate_links, deduplicate_listings
from app.utils.grouping import group_listings, sort_groups
from app.utils.interchange import InterchangeGroup, build_interchange_group
from app.utils.part_numbers import extract_part_numbers, normalize_query
from app.utils.query_analysis import QueryType, analyze_query
from app.utils.ranking import filter_market_listings, filter_salvage_hits, group_links_by_category, rank_listings

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
    vehicle_make: str | None = Query(None, description="User's vehicle make (e.g. Volvo, BMW) for personalized AI"),
    vehicle_model: str | None = Query(None, description="User's vehicle model (e.g. 940, E46)"),
    vehicle_year: str | None = Query(None, description="User's vehicle year (e.g. 1995)"),
    vin: str | None = Query(None, description="17-character VIN to decode and use for vehicle context"),
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

    # --- VIN Decoding (populate vehicle context) ---
    if vin and len(vin) == 17:
        try:
            from app.services.vin_decoder import decode_vin as _decode_vin

            vin_result = await _decode_vin(vin)
            if not vin_result.error:
                if vin_result.make and not vehicle_make:
                    vehicle_make = vin_result.make
                if vin_result.model and not vehicle_model:
                    vehicle_model = vin_result.model
                if vin_result.year and not vehicle_year:
                    vehicle_year = str(vin_result.year)
                logger.info(f"VIN {vin} decoded: {vehicle_year} {vehicle_make} {vehicle_model}")
        except Exception as e:
            logger.warning(f"VIN decode failed: {e}")

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

    # --- AI Advisor (runs in parallel with everything else) ---
    ai_task = asyncio.create_task(
        _safe_ai_analysis(query, vehicle_make=vehicle_make, vehicle_model=vehicle_model, vehicle_year=vehicle_year)
    )

    # --- Community Discussions (parallel, 5s timeout) ---
    community_task = asyncio.create_task(
        _safe_community_fetch(query, analysis.vehicle_hint, analysis.part_description, analysis.brands_found)
    )

    # --- Interchange Expansion (Phase 5) ---
    interchange_group: InterchangeGroup | None = None

    if analysis.query_type == QueryType.PART_NUMBER and settings.scrape_enabled:
        if settings.interchange_enabled:
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

    # --- Wait for AI analysis (it may provide OEM part numbers to search) ---
    ai_result: AIAdvisorResult | None = await ai_task

    # If AI found OEM part numbers and we didn't extract any, add them
    ai_part_numbers = []
    if ai_result and ai_result.oem_part_numbers:
        ai_part_numbers = ai_result.oem_part_numbers
        # Merge AI-found part numbers into extracted set
        for pn in ai_part_numbers:
            if pn not in extracted_part_numbers:
                extracted_part_numbers.append(pn)
        logger.info(f"AI advisor found OEM part numbers: {ai_part_numbers}")

    # Also add part numbers from AI recommendations
    ai_rec_part_numbers = []
    if ai_result and ai_result.recommendations:
        for rec in ai_result.recommendations:
            if rec.part_number and rec.part_number not in ai_rec_part_numbers:
                ai_rec_part_numbers.append(rec.part_number)

    # Enrich analysis with AI-found vehicle info
    if ai_result and ai_result.vehicle_make and not analysis.vehicle_hint:
        parts = [ai_result.vehicle_make]
        if ai_result.vehicle_model:
            parts.append(ai_result.vehicle_model)
        if ai_result.vehicle_generation:
            parts.append(ai_result.vehicle_generation)
        analysis.vehicle_hint = " ".join(parts)
        logger.info(f"AI enriched vehicle hint: {analysis.vehicle_hint}")
    if ai_result and ai_result.part_type and not analysis.part_description:
        analysis.part_description = ai_result.part_type

    # --- Smart Connector Routing (registry-driven) ---
    PART_NUMBER_SOURCES, VEHICLE_SOURCES, ALWAYS_SOURCES = _get_connector_routing()
    connectors = get_all_connectors()

    # Include AI-found part numbers in what we pass to connectors
    all_part_numbers = list(set(extracted_part_numbers + analysis.cross_references + ai_rec_part_numbers))
    shared_kwargs: dict[str, Any] = {
        "max_results": max_results,
        "zip_code": zip_code,
        "part_numbers": all_part_numbers,
    }

    # Pass AI vehicle context to resources connector for make-aware filtering
    if ai_result and ai_result.relevant_makes:
        shared_kwargs["relevant_makes"] = ai_result.relevant_makes
    if ai_result and ai_result.is_consumable:
        shared_kwargs["is_consumable"] = True

    tasks = []

    if analysis.query_type == QueryType.PART_NUMBER:
        active_sources = PART_NUMBER_SOURCES | ALWAYS_SOURCES
        for connector in connectors:
            if connector.source_name in active_sources:
                tasks.append(_run_connector(connector, normalized_query, shared_kwargs))

        if analysis.vehicle_hint and analysis.part_description:
            vehicle_query = f"{analysis.vehicle_hint} {analysis.part_description}".upper()
            vehicle_kwargs = {**shared_kwargs, "part_numbers": extracted_part_numbers}
            for connector in connectors:
                if connector.source_name in VEHICLE_SOURCES:
                    tasks.append(_run_connector(connector, vehicle_query, vehicle_kwargs))
        else:
            for connector in connectors:
                if connector.source_name in VEHICLE_SOURCES:
                    logger.info(f"Skipping {connector.source_name} for part number query (no vehicle context)")

        if interchange_group and interchange_group.interchange_numbers:
            interchange_pns = interchange_group.interchange_numbers[: settings.max_interchange_searches]
            interchange_sources = {"ebay", "rockauto", "partsgeek"}
            for pn in interchange_pns:
                for connector in connectors:
                    if connector.source_name in interchange_sources:
                        ic_kwargs = {**shared_kwargs, "part_numbers": [pn]}
                        tasks.append(_run_connector(connector, pn, ic_kwargs, matched_interchange=pn))
    else:
        # Vehicle+part or keyword queries: search all sources
        for connector in connectors:
            tasks.append(_run_connector(connector, normalized_query, shared_kwargs))

        # ALSO search with AI-found OEM part numbers (much more specific)
        if ai_part_numbers:
            for pn in ai_part_numbers[:2]:  # Top 2 OEM PNs
                for connector in connectors:
                    if connector.source_name in PART_NUMBER_SOURCES:
                        pn_kwargs = {**shared_kwargs, "part_numbers": [pn]}
                        tasks.append(_run_connector(connector, pn, pn_kwargs, matched_interchange=pn))

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

    # --- Filter wrong-vehicle market listings ---
    market_listings = filter_market_listings(market_listings, ai_result)

    # --- AI-driven filtering ---
    # Remove salvage results for consumable parts
    is_consumable = ai_result.is_consumable if ai_result else False
    if is_consumable:
        salvage_hits = []
        logger.info("Filtered salvage hits: part is consumable")

    # Filter external links by relevant makes (remove Ford/Honda links for BMW queries)
    relevant_makes = ai_result.relevant_makes if ai_result else []
    if relevant_makes:
        external_links = _filter_links_by_make(external_links, relevant_makes)

    # Relevance filtering: remove irrelevant salvage hits
    salvage_hits = filter_salvage_hits(salvage_hits, analysis)

    # Ranking / sorting (context-aware)
    market_listings = rank_listings(market_listings, normalized_query, sort, analysis)
    # Put AI-recommended brands/part numbers at the top so they’re not buried below other brands
    if ai_result and ai_result.recommendations and market_listings:
        _recommended_brands = {r.brand.lower().strip() for r in ai_result.recommendations}
        _recommended_pns = {r.part_number.upper().strip() for r in ai_result.recommendations}

        def _ai_match(ml: MarketListing) -> bool:
            if (ml.brand or "").lower() in _recommended_brands:
                return True
            if _recommended_pns and ml.part_numbers:
                listing_pns = {p.upper().strip() for p in ml.part_numbers}
                if _recommended_pns & listing_pns:
                    return True
            return False

        market_listings.sort(key=lambda m: (0 if _ai_match(m) else 1))
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
    # Put AI-recommended brands/part numbers at the top of the grouped list too
    if ai_result and ai_result.recommendations and sorted_groups:
        _rec_brands = {r.brand.lower().strip() for r in ai_result.recommendations}
        _rec_pns = {r.part_number.upper().strip() for r in ai_result.recommendations}

        def _group_ai_match(g: dict) -> bool:
            if (g.get("brand") or "").lower() in _rec_brands:
                return True
            if (g.get("part_number") or "").upper() in _rec_pns:
                return True
            return False

        sorted_groups.sort(key=lambda g: (0 if _group_ai_match(g) else 1))
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

    # --- Collect community results ---
    community_threads: list[CommunityThread] = await community_task
    community_sources = [
        CommunitySource(title=t.title, url=t.url, source="reddit", score=t.score) for t in community_threads
    ]

    # --- Resolve vehicle alias BEFORE building response (needed for fitment) ---
    resolved_vehicle_id: int | None = None
    resolved_config_id: int | None = None
    if vehicle_year or vehicle_make or vehicle_model:
        alias_parts = [
            p
            for p in (str(vehicle_year or "").strip(), (vehicle_make or "").strip(), (vehicle_model or "").strip())
            if p
        ]
        alias_text = " ".join(alias_parts)
        if alias_text:
            try:
                resolve_result = await resolve_vehicle_alias(alias_text, source_domain=None)
                resolved_vehicle_id = resolve_result.vehicle_id
                resolved_config_id = resolve_result.config_id
            except Exception as e:
                logger.warning("Vehicle resolver failed: %s", e)

    # --- Fitment Matching ---
    if resolved_vehicle_id and market_listings:
        try:
            all_pns = list({pn for ml in market_listings for pn in ml.part_numbers if pn})
            fitment_map = await check_fitments(all_pns, resolved_vehicle_id)
            if fitment_map:
                for ml in market_listings:
                    for pn in ml.part_numbers:
                        if pn in fitment_map:
                            ml.fitment_status = fitment_map[pn]
                            break
                logger.info(f"Fitment matched {len(fitment_map)} part numbers")
        except Exception as e:
            logger.warning(f"Fitment check failed: {e}")

    # Build intelligence data for the response
    intelligence = PartIntelligence(
        query_type=analysis.query_type.value,
        vehicle_hint=analysis.vehicle_hint,
        part_description=analysis.part_description,
        cross_references=analysis.cross_references,
        brands_found=analysis.brands_found,
        interchange=_build_interchange_info(interchange_group) if interchange_group else None,
        brand_comparison=brand_comparison,
        community_sources=community_sources,
    )

    # --- Build AI analysis for response ---
    ai_analysis = _build_ai_analysis(ai_result) if ai_result else None

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
        "ai_analysis": ai_analysis.model_dump() if ai_analysis else None,
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
            vehicle_id=resolved_vehicle_id,
            config_id=resolved_config_id,
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


# ── Helper functions ────────────────────────────────────────────────────


async def _safe_community_fetch(
    query: str,
    vehicle_hint: str | None = None,
    part_description: str | None = None,
    brands: list[str] | None = None,
) -> list[CommunityThread]:
    """Fetch community discussions with timeout and error handling."""
    try:
        return await asyncio.wait_for(
            fetch_community_discussions(query, vehicle_hint, part_description, brands),
            timeout=5,
        )
    except TimeoutError:
        logger.warning("Community fetch timed out after 5s")
        return []
    except Exception as e:
        logger.warning(f"Community fetch failed: {e}")
        return []


async def _safe_ai_analysis(
    query: str,
    vehicle_make: str | None = None,
    vehicle_model: str | None = None,
    vehicle_year: str | None = None,
) -> AIAdvisorResult | None:
    """Run AI analysis with timeout and error handling."""
    try:
        return await asyncio.wait_for(
            get_ai_recommendations(
                query,
                vehicle_make=vehicle_make,
                vehicle_model=vehicle_model,
                vehicle_year=vehicle_year,
            ),
            timeout=25,  # AI should be fast; don't block the whole search
        )
    except TimeoutError:
        logger.warning("AI advisor timed out after 25s")
        return None
    except Exception as e:
        logger.warning(f"AI advisor failed: {e}")
        return None


# Make-specific OEM dealer domains to filter
_MAKE_SPECIFIC_DOMAINS = {
    "ford": {"fordpartsgiant.com", "parts.ford.com"},
    "gm": {"gmpartsdirect.com", "parts.gm.com"},
    "chevrolet": {"gmpartsdirect.com", "parts.gm.com"},
    "mopar": {"moparpartsgiant.com", "parts.mopar.com"},
    "dodge": {"moparpartsgiant.com", "parts.mopar.com"},
    "chrysler": {"moparpartsgiant.com", "parts.mopar.com"},
    "jeep": {"moparpartsgiant.com", "parts.mopar.com"},
    "ram": {"moparpartsgiant.com", "parts.mopar.com"},
    "honda": {"hondapartsnow.com", "parts.honda.com"},
    "acura": {"parts.acura.com"},
    "toyota": {"toyotapartsdeal.com", "parts.toyota.com"},
    "lexus": {"lexuspartsnow.com", "parts.lexus.com"},
    "nissan": {"nissanpartsdeal.com", "parts.nissanusa.com"},
    "subaru": {"subarupartsdeal.com", "parts.subaru.com"},
    "mercedes": {"parts.mbusa.com"},
    "bmw": {"realoem.com"},
    "porsche": {"suncoastparts.com", "stoddard.com", "sierramadrecollection.com", "design911.com", "rosepassion.com"},
    "volvo": {"ipdusa.com", "swedishcarparts.com"},
    "audi": {"ecstuning.com"},
    "volkswagen": {"ecstuning.com"},
    "vw": {"ecstuning.com"},
}

# Universal stores that apply to all makes
_UNIVERSAL_DOMAINS = {
    "rockauto.com",
    "autozone.com",
    "oreillyauto.com",
    "advanceautoparts.com",
    "napaonline.com",
    "carparts.com",
    "1aauto.com",
    "partsgeek.com",
    "amazon.com",
    "ebay.com",
    "car-part.com",
    "lkqonline.com",
    "row52.com",
    "summitracing.com",
    "jegs.com",
    "youtube.com",
    "mcmaster.com",
    "grainger.com",
    "carid.com",
    "partsouq.com",
    "amayama.com",
    "megazip.net",
    "fcpeuro.com",
    "pelicanparts.com",
    "autohauzaz.com",
    "eeuroparts.com",
}


def _filter_links_by_make(links: list[ExternalLink], relevant_makes: list[str]) -> list[ExternalLink]:
    """Remove make-specific OEM dealer links that don't match the searched vehicle."""
    if not relevant_makes:
        return links

    makes_lower = {m.lower() for m in relevant_makes}

    # Collect domains that ARE relevant for these makes
    relevant_specific_domains: set[str] = set()
    for make in makes_lower:
        relevant_specific_domains.update(_MAKE_SPECIFIC_DOMAINS.get(make, set()))

    # Collect ALL make-specific domains
    all_specific_domains: set[str] = set()
    for domains in _MAKE_SPECIFIC_DOMAINS.values():
        all_specific_domains.update(domains)

    # Domains that are specific to OTHER makes (irrelevant)
    irrelevant_domains = all_specific_domains - relevant_specific_domains

    filtered = []
    for link in links:
        # Check if this link's URL contains an irrelevant domain
        url_lower = link.url.lower()
        is_irrelevant = any(domain in url_lower for domain in irrelevant_domains)
        if not is_irrelevant:
            filtered.append(link)

    removed = len(links) - len(filtered)
    if removed > 0:
        logger.info(f"Filtered {removed} make-irrelevant external links for makes: {relevant_makes}")

    return filtered


def _build_ai_analysis(result: AIAdvisorResult) -> AIAnalysis | None:
    """Convert AIAdvisorResult to the API schema."""
    if result.error and not result.recommendations:
        return AIAnalysis(error=result.error)

    recommendations = [
        AIRecommendation(
            rank=rec.rank,
            grade=rec.grade,
            brand=rec.brand,
            part_number=rec.part_number,
            title=rec.title,
            why=rec.why,
            quality_tier=rec.quality_tier,
            quality_score=rec.quality_score,
            estimated_price_low=rec.estimated_price_low,
            estimated_price_high=rec.estimated_price_high,
            best_retailers=rec.best_retailers,
            buy_links=[BuyLink(store=bl["store"], url=bl["url"]) for bl in rec.buy_links],
        )
        for rec in result.recommendations
    ]

    avoid = [AIAvoidItem(brand=item.brand, reason=item.reason) for item in result.avoid]

    return AIAnalysis(
        vehicle_make=result.vehicle_make,
        vehicle_model=result.vehicle_model,
        vehicle_generation=result.vehicle_generation,
        vehicle_years=result.vehicle_years,
        part_type=result.part_type,
        is_consumable=result.is_consumable,
        oem_part_numbers=result.oem_part_numbers,
        recommendations=recommendations,
        avoid=avoid,
        notes=result.notes,
        relevant_makes=result.relevant_makes,
    )
