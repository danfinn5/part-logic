"""
Singleton async Playwright browser manager.

Lazily initializes a Chromium browser on first use.
Shared across all Playwright-based connectors.
Uses stealth settings to reduce bot detection.
"""

import logging
from contextlib import asynccontextmanager

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton state
_playwright = None
_browser = None


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
    context = await browser.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        timezone_id="America/New_York",
        java_script_enabled=True,
    )
    context.set_default_timeout(timeout_ms)

    page = await context.new_page()

    # Stealth: override navigator.webdriver to be undefined
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
