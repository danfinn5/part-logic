"""
Search API route - main endpoint for part searches.
Uses connector registry and parallel execution.
"""
import asyncio
from fastapi import APIRouter, Query
from typing import Optional, Dict, Any
import redis.asyncio as redis
import json
import logging
from app.schemas.search import (
    SearchResponse, SearchResults, SourceStatus,
    MarketListing, SalvageHit, ExternalLink,
)
from app.ingestion import get_all_connectors
from app.ingestion.base import BaseConnector
from app.utils.part_numbers import extract_part_numbers, normalize_query
from app.utils.deduplication import deduplicate_listings, deduplicate_links
from app.utils.ranking import rank_listings, group_links_by_category
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

# Redis client (will be initialized in startup)
redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = await redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
    return redis_client


async def get_cached_result(cache_key: str) -> Optional[dict]:
    """Get cached result from Redis."""
    try:
        client = await get_redis_client()
        cached = await client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis cache read error: {e}")
    return None


async def set_cached_result(cache_key: str, result: dict):
    """Cache result in Redis."""
    try:
        client = await get_redis_client()
        await client.setex(
            cache_key,
            settings.cache_ttl_seconds,
            json.dumps(result)
        )
    except Exception as e:
        logger.warning(f"Redis cache write error: {e}")


async def _run_connector(
    connector: BaseConnector,
    query: str,
    extra_kwargs: Dict[str, Any],
) -> Dict[str, Any]:
    """Run a single connector with per-source caching, timeout, and error handling."""
    source_name = connector.source_name

    # Check source-specific cache first
    cache_key = connector.get_cache_key(query)
    cached = await get_cached_result(cache_key)
    if cached:
        logger.info(f"Serving cached {source_name} result")
        return {**cached, "_status": "cached", "_source": source_name}

    try:
        result = await asyncio.wait_for(
            connector.search(query, **extra_kwargs),
            timeout=settings.connector_timeout,
        )
        # Cache the result
        await set_cached_result(cache_key, result)
        result["_status"] = "ok" if not result.get("error") else "error"
        result["_source"] = source_name
        return result

    except asyncio.TimeoutError:
        logger.error(f"{source_name} timed out after {settings.connector_timeout}s")
        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": [],
            "error": f"Timed out after {settings.connector_timeout}s",
            "_status": "error",
            "_source": source_name,
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
        }


@router.get("", response_model=SearchResponse)
async def search_parts(
    query: str = Query(..., description="Search query (part number, keywords, etc.)"),
    zip_code: Optional[str] = Query(None, description="Zip code for location-based searches"),
    max_results: int = Query(20, ge=1, le=50, description="Max results per source"),
    sort: str = Query("relevance", description="Sort order: relevance, price_asc, price_desc"),
):
    """
    Search for parts across multiple sources in parallel.

    Sources include eBay (API when configured), RockAuto, Row52, Car-Part.com,
    Partsouq, ECS Tuning, FCP Euro, Amazon Automotive, PartsGeek,
    and repair resources (YouTube, Charm.li).

    Results are cached for 6 hours per (source, query) combination.
    """
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

    # Build kwargs for each connector
    shared_kwargs: Dict[str, Any] = {
        "max_results": max_results,
        "zip_code": zip_code,
        "part_numbers": extracted_part_numbers,
    }

    # Fan out to all connectors in parallel
    connectors = get_all_connectors()
    tasks = [
        _run_connector(connector, normalized_query, shared_kwargs)
        for connector in connectors
    ]
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

        # Parse raw dicts back into models if they came from cache
        for item in result.get("market_listings", []):
            if isinstance(item, dict):
                market_listings.append(MarketListing(**item))
            else:
                market_listings.append(item)

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
        sources_queried.append(SourceStatus(
            source=source_name,
            status=status,
            details=error_msg or "Success",
            result_count=result_count,
        ))

        if error_msg:
            warnings.append(f"{source_name}: {error_msg}")

    # Deduplication
    market_listings = deduplicate_listings(market_listings)
    external_links = deduplicate_links(external_links)

    # Ranking / sorting
    market_listings = rank_listings(market_listings, normalized_query, sort)
    external_links = group_links_by_category(external_links)

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
        "sources_queried": [s.model_dump() for s in sources_queried],
        "warnings": warnings,
        "cached": False,
    }

    # Cache overall result
    await set_cached_result(overall_cache_key, response_data)

    return SearchResponse(**response_data)
