"""
Admin API for the source registry.
List, filter, search, and manage parts sources.
"""

from fastapi import APIRouter, Query

from app.data.source_registry import (
    get_active_sources,
    get_all_sources,
    get_registry_stats,
    get_source,
    set_source_priority,
    toggle_source_status,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
async def list_sources(
    source_type: str | None = Query(None, description="Filter: buyable or reference"),
    category: str | None = Query(None, description="Filter by category"),
    tag: str | None = Query(None, description="Filter by tag"),
    status: str | None = Query(None, description="Filter: active or disabled"),
    search: str | None = Query(None, description="Search by domain or name"),
):
    """List all sources with optional filters."""
    if source_type or category or tag:
        sources = get_active_sources(source_type=source_type, category=category, tag=tag)
        if status == "disabled":
            # get_active_sources only returns active, need to filter differently
            all_sources = get_all_sources()
            sources = [s for s in all_sources if s.get("status") == "disabled"]
            if source_type:
                sources = [s for s in sources if s.get("source_type") == source_type]
            if category:
                sources = [s for s in sources if s.get("category") == category]
            if tag:
                sources = [s for s in sources if tag in s.get("tags", [])]
    else:
        sources = get_all_sources()
        if status:
            sources = [s for s in sources if s.get("status") == status]

    if search:
        q = search.lower()
        sources = [s for s in sources if q in s["domain"] or q in s["name"].lower()]

    return {"sources": sources, "count": len(sources)}


@router.get("/stats")
async def source_stats():
    """Get summary statistics about the source registry."""
    return get_registry_stats()


@router.get("/{domain:path}")
async def get_source_detail(domain: str):
    """Get a single source by domain."""
    source = get_source(domain)
    if not source:
        return {"error": f"Source not found: {domain}"}
    return source


@router.post("/{domain:path}/toggle")
async def toggle_status(domain: str):
    """Toggle a source between active and disabled."""
    source = toggle_source_status(domain)
    if not source:
        return {"error": f"Source not found: {domain}"}
    return source


@router.post("/{domain:path}/priority")
async def update_priority(domain: str, priority: int = Query(..., ge=0, le=100)):
    """Set priority for a source (0-100)."""
    source = set_source_priority(domain, priority)
    if not source:
        return {"error": f"Source not found: {domain}"}
    return source
