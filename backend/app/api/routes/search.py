"""
Search API route - main endpoint for part searches.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import redis.asyncio as redis
import json
import logging
from app.schemas.search import SearchResponse, SourceStatus
from app.ingestion.ebay import eBayConnector
from app.ingestion.rockauto import RockAutoConnector
from app.ingestion.row52 import Row52Connector
from app.ingestion.carpart import CarPartConnector
from app.ingestion.partsouq import PartsouqConnector
from app.utils.part_numbers import extract_part_numbers, normalize_query
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

# Initialize connectors
ebay_connector = eBayConnector()
rockauto_connector = RockAutoConnector()
row52_connector = Row52Connector()
carpart_connector = CarPartConnector()
partsouq_connector = PartsouqConnector()

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


@router.get("", response_model=SearchResponse)
async def search_parts(
    query: str = Query(..., description="Search query (part number, keywords, etc.)"),
    zip_code: Optional[str] = Query(None, description="Zip code for location-based searches"),
    max_results: int = Query(20, ge=1, le=50, description="Max results per source")
):
    """
    Search for parts across multiple sources.
    
    Queries:
    - eBay (API)
    - RockAuto (scraping)
    - Row52 (scraping)
    - Car-Part.com (link only)
    - Partsouq (placeholder)
    
    Results are cached for 6 hours per (source, query) combination.
    """
    normalized_query = normalize_query(query)
    extracted_part_numbers = extract_part_numbers(normalized_query)
    
    # Check for cached overall result first
    overall_cache_key = f"search:overall:{normalized_query}"
    cached_overall = await get_cached_result(overall_cache_key)
    
    if cached_overall:
        logger.info(f"Serving cached result for query: {normalized_query}")
        response = SearchResponse(**cached_overall)
        response.cached = True
        return response
    
    # Initialize response structure
    market_listings = []
    salvage_hits = []
    external_links = []
    sources_queried = []
    warnings = []
    
    # Query each source
    sources = [
        ("ebay", ebay_connector, {}),
        ("rockauto", rockauto_connector, {}),
        ("row52", row52_connector, {}),
        ("carpart", carpart_connector, {"zip_code": zip_code}),
        ("partsouq", partsouq_connector, {}),
    ]
    
    for source_name, connector, extra_kwargs in sources:
        try:
            # Check source-specific cache
            cache_key = connector.get_cache_key(normalized_query)
            cached = await get_cached_result(cache_key)
            
            if cached:
                logger.info(f"Serving cached {source_name} result")
                market_listings.extend(cached.get("market_listings", []))
                salvage_hits.extend(cached.get("salvage_hits", []))
                external_links.extend(cached.get("external_links", []))
                sources_queried.append(SourceStatus(
                    source=source_name,
                    status="cached",
                    details="Served from cache",
                    result_count=len(cached.get("market_listings", [])) + 
                               len(cached.get("salvage_hits", [])) + 
                               len(cached.get("external_links", []))
                ))
            else:
                # Query the source
                logger.info(f"Querying {source_name} for: {normalized_query}")
                result = await connector.search(
                    normalized_query,
                    max_results=max_results,
                    **extra_kwargs
                )
                
                # Cache the result
                await set_cached_result(cache_key, result)
                
                # Aggregate results
                market_listings.extend(result.get("market_listings", []))
                salvage_hits.extend(result.get("salvage_hits", []))
                external_links.extend(result.get("external_links", []))
                
                # Record source status
                status = "ok" if not result.get("error") else "error"
                error_msg = result.get("error")
                result_count = len(result.get("market_listings", [])) + \
                              len(result.get("salvage_hits", [])) + \
                              len(result.get("external_links", []))
                
                sources_queried.append(SourceStatus(
                    source=source_name,
                    status=status,
                    details=error_msg or "Success",
                    result_count=result_count
                ))
                
                if error_msg:
                    warnings.append(f"{source_name}: {error_msg}")
        
        except Exception as e:
            logger.error(f"Error querying {source_name}: {e}")
            sources_queried.append(SourceStatus(
                source=source_name,
                status="error",
                details=str(e),
                result_count=0
            ))
            warnings.append(f"{source_name}: {str(e)}")
    
    # Build response
    response_data = {
        "query": normalized_query,
        "extracted_part_numbers": extracted_part_numbers,
        "results": {
            "market_listings": [listing.dict() for listing in market_listings],
            "salvage_hits": [hit.dict() for hit in salvage_hits],
            "external_links": [link.dict() for link in external_links]
        },
        "sources_queried": [status.dict() for status in sources_queried],
        "warnings": warnings,
        "cached": False
    }
    
    # Cache overall result
    await set_cached_result(overall_cache_key, response_data)
    
    return SearchResponse(**response_data)
