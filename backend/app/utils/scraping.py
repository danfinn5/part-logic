"""
Shared scraping utilities for HTTP-based connectors.
"""
import random
import httpx
import logging
from typing import Tuple, Optional
from app.utils.normalization import normalize_price

logger = logging.getLogger(__name__)

# Desktop Chrome User-Agents for rotation
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


def get_random_ua() -> str:
    """Return a random desktop Chrome User-Agent."""
    return random.choice(_USER_AGENTS)


def default_headers() -> dict:
    """Return default browser-like headers."""
    return {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }


async def fetch_html(url: str, headers: Optional[dict] = None, timeout: int = 15) -> Tuple[str, int]:
    """
    Fetch HTML from a URL with browser-like headers.

    Returns (html_content, status_code).
    Raises on network errors.
    """
    merged_headers = default_headers()
    if headers:
        merged_headers.update(headers)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers=merged_headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text, response.status_code


async def fetch_json(url: str, headers: Optional[dict] = None, timeout: int = 15) -> Tuple[dict, int]:
    """
    Fetch JSON from a URL with browser-like headers.

    Returns (json_data, status_code).
    Raises on network errors.
    """
    merged_headers = default_headers()
    merged_headers["Accept"] = "application/json"
    if headers:
        merged_headers.update(headers)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers=merged_headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json(), response.status_code


def parse_price(text: str) -> float:
    """
    Extract a price from messy HTML text.
    Wraps normalize_price with additional cleanup for HTML artifacts.
    """
    if not text:
        return 0.0
    # Strip common HTML artifacts
    cleaned = text.strip().replace("\n", "").replace("\t", "").replace("\xa0", " ")
    # Try to find a price pattern in the text
    import re
    match = re.search(r'[\$€£]?\s*[\d,]+\.?\d*', cleaned)
    if match:
        return normalize_price(match.group(0))
    return normalize_price(cleaned)
