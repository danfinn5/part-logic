"""
Shared scraping utilities for HTTP-based connectors.

Provides fetch_html/fetch_json with:
- Rotating modern User-Agents
- Retry with exponential backoff
- Browser-like headers
- Price parsing from messy HTML text
"""

import asyncio
import logging
import random
import re

import httpx

from app.utils.normalization import normalize_price

logger = logging.getLogger(__name__)

# Modern Chrome User-Agents (2025-era)
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
]


def get_random_ua() -> str:
    """Return a random desktop browser User-Agent."""
    return random.choice(_USER_AGENTS)


def default_headers() -> dict:
    """Return default browser-like headers."""
    return {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Chromium";v="131", "Google Chrome";v="131", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }


async def fetch_html(
    url: str,
    headers: dict | None = None,
    timeout: int = 15,
    retries: int = 2,
    backoff: float = 1.0,
) -> tuple[str, int]:
    """
    Fetch HTML from a URL with browser-like headers and retry logic.

    Returns (html_content, status_code).
    Raises on network errors after all retries exhausted.
    """
    merged_headers = default_headers()
    if headers:
        merged_headers.update(headers)

    last_error = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers=merged_headers,
                http2=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text, response.status_code
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
            last_error = e
            if attempt < retries:
                wait = backoff * (2**attempt) + random.uniform(0, 0.5)
                logger.info(f"Retry {attempt + 1}/{retries} for {url} after {wait:.1f}s ({e})")
                await asyncio.sleep(wait)
            else:
                raise
        except Exception:
            raise

    raise last_error  # unreachable but satisfies type checker


async def fetch_json(
    url: str,
    headers: dict | None = None,
    timeout: int = 15,
    retries: int = 1,
) -> tuple[dict, int]:
    """
    Fetch JSON from a URL with browser-like headers.

    Returns (json_data, status_code).
    Raises on network errors.
    """
    merged_headers = default_headers()
    merged_headers["Accept"] = "application/json"
    if headers:
        merged_headers.update(headers)

    last_error = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers=merged_headers,
                http2=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json(), response.status_code
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
            last_error = e
            if attempt < retries:
                wait = 1.0 * (2**attempt)
                await asyncio.sleep(wait)
            else:
                raise

    raise last_error


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
    match = re.search(r"[\$€£]?\s*[\d,]+\.?\d*", cleaned)
    if match:
        return normalize_price(match.group(0))
    return normalize_price(cleaned)
