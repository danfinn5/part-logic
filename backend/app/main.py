"""
PartLogic FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import search, sources
from app.api.routes.canonical import router as canonical_router
from app.api.routes.history import router as history_router
from app.config import settings
from app.db import close_db, get_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    logger.info("Starting PartLogic API...")
    try:
        await search.get_redis_client()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.warning(f"Redis connection failed (caching disabled): {e}")

    try:
        await get_db()
        logger.info("SQLite database initialized")
    except Exception as e:
        logger.warning(f"SQLite initialization failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down PartLogic API...")
    if search.redis_client:
        await search.redis_client.close()
        logger.info("Redis connection closed")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router)
app.include_router(sources.router)
app.include_router(canonical_router)
app.include_router(history_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PartLogic API",
        "version": settings.api_version,
        "endpoints": {
            "search": "/search?query=...",
            "sources": "/sources",
            "sources_stats": "/sources/stats",
            "history": "/history/searches",
            "price_history": "/history/prices",
            "canonical": "/canonical",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
