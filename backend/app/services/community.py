"""
Reddit community integration for PartLogic.

Fetches relevant discussions from automotive subreddits using Reddit's
public JSON API (no auth required). Results are cached in Redis.
"""

import asyncio
import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Map vehicle makes to specific subreddits
MAKE_SUBREDDITS: dict[str, list[str]] = {
    "bmw": ["BMW", "BmwTech"],
    "porsche": ["Porsche"],
    "audi": ["Audi"],
    "volkswagen": ["Volkswagen", "tdi"],
    "vw": ["Volkswagen", "tdi"],
    "volvo": ["Volvo"],
    "mercedes": ["mercedes_benz", "MercedesBenz"],
    "mercedes-benz": ["mercedes_benz", "MercedesBenz"],
    "toyota": ["Toyota", "ToyotaTacoma", "4Runner"],
    "honda": ["Honda", "CivicSi"],
    "subaru": ["subaru", "WRX"],
    "ford": ["Ford", "FordTrucks"],
    "chevrolet": ["Chevrolet", "Corvette"],
    "mazda": ["mazda", "Miata"],
    "nissan": ["Nissan", "350z"],
    "lexus": ["Lexus"],
    "hyundai": ["Hyundai"],
    "kia": ["kia"],
    "jeep": ["Jeep"],
    "dodge": ["Dodge"],
    "mini": ["MINI"],
}

# Always-searched subreddits
GENERAL_SUBS = ["MechanicAdvice", "AutoDIY", "cars"]


@dataclass
class CommunityThread:
    title: str
    url: str
    subreddit: str
    score: int


async def fetch_community_discussions(
    query: str,
    vehicle_hint: str | None = None,
    part_description: str | None = None,
    brands: list[str] | None = None,
) -> list[CommunityThread]:
    """Fetch relevant Reddit discussions for a parts query."""
    if not settings.community_enabled:
        return []

    # Check cache first
    cached = await _get_cached_community(query)
    if cached is not None:
        return cached

    # Build subreddit list
    subs = list(GENERAL_SUBS)
    if vehicle_hint:
        hint_lower = vehicle_hint.lower()
        for make, make_subs in MAKE_SUBREDDITS.items():
            if make in hint_lower:
                subs.extend(make_subs)
                break

    # Build search query
    search_terms = []
    if part_description:
        search_terms.append(part_description)
    if vehicle_hint:
        search_terms.append(vehicle_hint)
    if not search_terms:
        search_terms.append(query)
    search_query = " ".join(search_terms)

    # Fetch from each subreddit in parallel
    tasks = [_search_subreddit(sub, search_query) for sub in set(subs)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten and filter
    threads: list[CommunityThread] = []
    for result in results:
        if isinstance(result, Exception):
            continue
        threads.extend(result)

    # Sort by score and deduplicate by URL
    seen_urls: set[str] = set()
    unique_threads: list[CommunityThread] = []
    for t in sorted(threads, key=lambda t: t.score, reverse=True):
        if t.url not in seen_urls:
            seen_urls.add(t.url)
            unique_threads.append(t)

    final = unique_threads[:10]

    # Cache result
    await _cache_community(query, final)

    return final


async def _search_subreddit(subreddit: str, query: str) -> list[CommunityThread]:
    """Search a single subreddit via Reddit's public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {
        "q": query,
        "sort": "relevance",
        "limit": "5",
        "restrict_sr": "on",
        "t": "all",
    }
    headers = {
        "User-Agent": settings.reddit_user_agent,
    }

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(url, params=params, headers=headers, follow_redirects=True)
            if response.status_code == 429:
                logger.warning(f"Reddit rate limited on r/{subreddit}")
                return []
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.warning(f"Reddit search failed for r/{subreddit}: {e}")
        return []

    threads: list[CommunityThread] = []
    children = data.get("data", {}).get("children", [])
    for child in children:
        post = child.get("data", {})
        score = post.get("score", 0)
        title = post.get("title", "")
        permalink = post.get("permalink", "")

        # Filter low-quality / removed posts
        if score < 5:
            continue
        if post.get("removed_by_category"):
            continue
        if not title or not permalink:
            continue

        threads.append(
            CommunityThread(
                title=title,
                url=f"https://www.reddit.com{permalink}",
                subreddit=subreddit,
                score=score,
            )
        )

    return threads


async def _get_cached_community(query: str) -> list[CommunityThread] | None:
    """Check Redis cache for community results."""
    try:
        from app.api.routes.search import get_cached_result

        normalized = query.lower().strip()
        data = await get_cached_result(f"community:{normalized}")
        if data is not None:
            return [CommunityThread(**t) for t in data]
    except Exception:
        pass
    return None


async def _cache_community(query: str, threads: list[CommunityThread]):
    """Cache community results in Redis."""
    try:
        from dataclasses import asdict

        from app.api.routes.search import set_cached_result

        normalized = query.lower().strip()
        await set_cached_result(
            f"community:{normalized}",
            [asdict(t) for t in threads],
            ttl=settings.community_cache_ttl,
        )
    except Exception as e:
        logger.warning(f"Failed to cache community results: {e}")
