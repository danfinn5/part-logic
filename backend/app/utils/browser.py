"""
Singleton async Playwright browser manager.

Lazily initializes a Chromium browser on first use.
Shared across all Playwright-based connectors.
Uses playwright-stealth for comprehensive bot detection evasion.
"""

import logging
import random
from contextlib import asynccontextmanager

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton state
_playwright = None
_browser = None

# Viewport and User-Agent rotation pools
_VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1920, "height": 1080},
    {"width": 1280, "height": 800},
]

_USER_AGENTS = [
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
]

# Try to import playwright-stealth; fall back gracefully
try:
    from playwright_stealth import Stealth

    _stealth = Stealth()
    _HAS_STEALTH = True
    logger.debug("playwright-stealth loaded")
except ImportError:
    _stealth = None
    _HAS_STEALTH = False
    logger.debug("playwright-stealth not installed, using manual stealth")


async def _ensure_browser():
    """Lazily start Playwright and launch Chromium."""
    global _playwright, _browser

    if _browser is not None:
        return _browser

    if not settings.playwright_enabled:
        raise RuntimeError("Playwright is disabled via config (playwright_enabled=false)")

    try:
        from playwright.async_api import async_playwright

        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ],
        )
        logger.info("Playwright Chromium browser launched")
        return _browser
    except Exception as e:
        logger.error(f"Failed to launch Playwright browser: {e}")
        raise


@asynccontextmanager
async def get_page(timeout_ms: int | None = None):
    """
    Context manager that creates a new browser page and closes it on exit.
    Applies stealth settings to reduce bot detection.

    Usage:
        async with get_page() as page:
            await page.goto("https://example.com")
            html = await page.content()
    """
    if timeout_ms is None:
        timeout_ms = settings.connector_timeout * 1000

    browser = await _ensure_browser()

    # Randomize viewport and user-agent per context
    viewport = random.choice(_VIEWPORTS)
    user_agent = random.choice(_USER_AGENTS)

    context = await browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale="en-US",
        timezone_id="America/New_York",
        java_script_enabled=True,
    )
    context.set_default_timeout(timeout_ms)

    # Apply stealth: prefer playwright-stealth, fall back to manual init_script
    if _HAS_STEALTH and _stealth is not None:
        await _stealth.apply_stealth_async(context)
    else:
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)
        try:
            yield page
        finally:
            await page.close()
            await context.close()
        return

    page = await context.new_page()

    try:
        yield page
    finally:
        await page.close()
        await context.close()


async def close_browser():
    """Shut down the browser and Playwright (call on app shutdown)."""
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
    logger.info("Playwright browser closed")
