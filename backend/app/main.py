"""
PartLogic FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.config import settings
from app.api.routes import search

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PartLogic API",
        "version": settings.api_version,
        "endpoints": {
            "search": "/search?query=...",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup():
    """Startup event - initialize Redis connection."""
    logger.info("Starting PartLogic API...")
    try:
        # Initialize Redis connection
        await search.get_redis_client()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.warning(f"Redis connection failed (caching disabled): {e}")


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event - close Redis connection."""
    logger.info("Shutting down PartLogic API...")
    if search.redis_client:
        await search.redis_client.close()
        logger.info("Redis connection closed")
