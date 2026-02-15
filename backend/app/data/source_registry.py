"""
JSON-backed source registry for all parts search sources.

Stores metadata about every known parts source: retailers, marketplaces,
OEM catalogs, salvage yards, EPCs, industrial suppliers, etc.

Each source has:
- domain (unique key), name, category, tags, notes
- source_type (buyable vs reference)
- status (active/disabled), priority (for ranking)
- crawler hints (supports_vin, supports_part_number_search, robots_policy, sitemap_url)
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

# Registry file location
_REGISTRY_PATH = Path(__file__).parent / "sources_registry.json"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_domain(raw: str) -> str:
    """
    Normalize a domain string: strip scheme, paths, whitespace; lowercase.
    Examples:
        "https://www.RockAuto.com/en/"  -> "rockauto.com"
        "facebook.com/marketplace"       -> "facebook.com/marketplace" (keep meaningful paths)
        "  EBAY.COM  "                   -> "ebay.com"
    """
    raw = raw.strip().lower()
    # Strip scheme
    if "://" in raw:
        parsed = urlparse(raw)
        raw = parsed.netloc + parsed.path
    # Strip www.
    if raw.startswith("www."):
        raw = raw[4:]
    # Strip trailing slash unless it's a meaningful path
    raw = raw.rstrip("/")
    return raw


def parse_tags(raw: str) -> list[str]:
    """Parse comma-separated tags string into sorted unique list."""
    if not raw or not raw.strip():
        return []
    tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
    return sorted(set(tags))


def _load_registry() -> dict[str, dict]:
    """Load the registry from disk. Returns {domain: source_dict}."""
    if not _REGISTRY_PATH.exists():
        return {}
    with open(_REGISTRY_PATH) as f:
        data = json.load(f)
    return {s["domain"]: s for s in data}


def _save_registry(registry: dict[str, dict]) -> None:
    """Save the registry to disk."""
    sources = sorted(registry.values(), key=lambda s: (s.get("source_type", ""), s.get("category", ""), s["domain"]))
    with open(_REGISTRY_PATH, "w") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)


def get_all_sources() -> list[dict]:
    """Get all sources, sorted by priority (high first) then domain."""
    registry = _load_registry()
    sources = list(registry.values())
    sources.sort(key=lambda s: (-s.get("priority", 50), s["domain"]))
    return sources


def get_source(domain: str) -> dict | None:
    """Get a single source by domain."""
    registry = _load_registry()
    return registry.get(normalize_domain(domain))


def get_active_sources(
    source_type: str | None = None,
    category: str | None = None,
    tag: str | None = None,
) -> list[dict]:
    """Get active sources with optional filters."""
    sources = get_all_sources()
    results = []
    for s in sources:
        if s.get("status") != "active":
            continue
        if source_type and s.get("source_type") != source_type:
            continue
        if category and s.get("category") != category:
            continue
        if tag and tag not in s.get("tags", []):
            continue
        results.append(s)
    return results


def upsert_source(
    domain: str,
    name: str,
    category: str,
    tags: list[str],
    notes: str = "",
    source_type: str = "buyable",
    status: str = "active",
    priority: int = 50,
    supports_vin: bool = False,
    supports_part_number_search: bool = True,
    robots_policy: str = "unknown",
    sitemap_url: str | None = None,
) -> dict:
    """Insert or update a source by domain (natural key)."""
    registry = _load_registry()
    domain = normalize_domain(domain)
    now = _now_iso()

    existing = registry.get(domain)
    if existing:
        # Update
        existing.update(
            {
                "name": name,
                "category": category,
                "tags": tags,
                "notes": notes,
                "source_type": source_type,
                "status": status,
                "priority": priority,
                "supports_vin": supports_vin,
                "supports_part_number_search": supports_part_number_search,
                "robots_policy": robots_policy,
                "sitemap_url": sitemap_url,
                "updated_at": now,
            }
        )
        source = existing
    else:
        # Insert
        source = {
            "id": str(uuid.uuid4()),
            "domain": domain,
            "name": name,
            "category": category,
            "tags": tags,
            "notes": notes,
            "source_type": source_type,
            "status": status,
            "priority": priority,
            "supports_vin": supports_vin,
            "supports_part_number_search": supports_part_number_search,
            "robots_policy": robots_policy,
            "sitemap_url": sitemap_url,
            "created_at": now,
            "updated_at": now,
        }
        registry[domain] = source

    _save_registry(registry)
    return source


def toggle_source_status(domain: str) -> dict | None:
    """Toggle a source between active and disabled."""
    registry = _load_registry()
    domain = normalize_domain(domain)
    source = registry.get(domain)
    if not source:
        return None
    source["status"] = "disabled" if source["status"] == "active" else "active"
    source["updated_at"] = _now_iso()
    _save_registry(registry)
    return source


def set_source_priority(domain: str, priority: int) -> dict | None:
    """Set priority for a source."""
    registry = _load_registry()
    domain = normalize_domain(domain)
    source = registry.get(domain)
    if not source:
        return None
    source["priority"] = priority
    source["updated_at"] = _now_iso()
    _save_registry(registry)
    return source


def get_registry_stats() -> dict:
    """Get summary stats about the registry."""
    sources = get_all_sources()
    stats = {
        "total": len(sources),
        "active": sum(1 for s in sources if s.get("status") == "active"),
        "disabled": sum(1 for s in sources if s.get("status") == "disabled"),
        "by_source_type": {},
        "by_category": {},
    }
    for s in sources:
        st = s.get("source_type", "unknown")
        stats["by_source_type"][st] = stats["by_source_type"].get(st, 0) + 1
        cat = s.get("category", "unknown")
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
    return stats
