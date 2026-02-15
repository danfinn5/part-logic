"""
SQLite database layer for PartLogic.

Stores:
- search_history: every search query with timestamp, result counts, analysis
- price_snapshots: price observations for (source, part_number, brand) over time
- user_preferences: key-value store for user settings (future use)

Uses aiosqlite for async SQLite access. The database file lives at
backend/data/partlogic.db and is auto-created on first startup.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# Database file location (next to CSV/JSON data files)
DB_PATH = Path(__file__).parent.parent / "data" / "partlogic.db"

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Get or create the database connection."""
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_tables(_db)
        logger.info(f"SQLite database initialized at {DB_PATH}")
    return _db


async def close_db():
    """Close the database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("SQLite database connection closed")


async def _init_tables(db: aiosqlite.Connection):
    """Create tables if they don't exist."""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            normalized_query TEXT NOT NULL,
            query_type TEXT,
            vehicle_hint TEXT,
            part_description TEXT,
            sort TEXT DEFAULT 'relevance',
            market_listing_count INTEGER DEFAULT 0,
            salvage_hit_count INTEGER DEFAULT 0,
            external_link_count INTEGER DEFAULT 0,
            source_count INTEGER DEFAULT 0,
            has_interchange INTEGER DEFAULT 0,
            cached INTEGER DEFAULT 0,
            response_time_ms INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_search_history_query
            ON search_history(normalized_query);
        CREATE INDEX IF NOT EXISTS idx_search_history_created
            ON search_history(created_at);

        CREATE TABLE IF NOT EXISTS price_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            source TEXT NOT NULL,
            part_number TEXT,
            brand TEXT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            shipping_cost REAL DEFAULT 0,
            condition TEXT,
            url TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_price_part_number
            ON price_snapshots(part_number);
        CREATE INDEX IF NOT EXISTS idx_price_source
            ON price_snapshots(source);
        CREATE INDEX IF NOT EXISTS idx_price_created
            ON price_snapshots(created_at);
        CREATE INDEX IF NOT EXISTS idx_price_brand_part
            ON price_snapshots(brand, part_number);

        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    await db.commit()


# ─── Search History ──────────────────────────────────────────────────


async def record_search(
    query: str,
    normalized_query: str,
    query_type: str = None,
    vehicle_hint: str = None,
    part_description: str = None,
    sort: str = "relevance",
    market_listing_count: int = 0,
    salvage_hit_count: int = 0,
    external_link_count: int = 0,
    source_count: int = 0,
    has_interchange: bool = False,
    cached: bool = False,
    response_time_ms: int = None,
) -> int:
    """Record a search in history. Returns the row ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO search_history
           (query, normalized_query, query_type, vehicle_hint, part_description,
            sort, market_listing_count, salvage_hit_count, external_link_count,
            source_count, has_interchange, cached, response_time_ms, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            query,
            normalized_query,
            query_type,
            vehicle_hint,
            part_description,
            sort,
            market_listing_count,
            salvage_hit_count,
            external_link_count,
            source_count,
            int(has_interchange),
            int(cached),
            response_time_ms,
            datetime.now(UTC).isoformat(),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def get_recent_searches(limit: int = 20) -> list[dict]:
    """Get the most recent searches."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM search_history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_popular_searches(limit: int = 20, days: int = 7) -> list[dict]:
    """Get most frequent searches in the last N days."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT normalized_query, COUNT(*) as count,
                  AVG(market_listing_count) as avg_listings,
                  MAX(created_at) as last_searched
           FROM search_history
           WHERE created_at > datetime('now', ?)
           GROUP BY normalized_query
           ORDER BY count DESC
           LIMIT ?""",
        (f"-{days} days", limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_search_stats() -> dict:
    """Get overall search statistics."""
    db = await get_db()

    cursor = await db.execute("SELECT COUNT(*) FROM search_history")
    total = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(DISTINCT normalized_query) FROM search_history")
    unique = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT AVG(market_listing_count), AVG(response_time_ms) FROM search_history")
    row = await cursor.fetchone()
    avg_listings = row[0] or 0
    avg_response = row[1] or 0

    cursor = await db.execute(
        """SELECT query_type, COUNT(*) as count
           FROM search_history
           WHERE query_type IS NOT NULL
           GROUP BY query_type
           ORDER BY count DESC"""
    )
    type_breakdown = [dict(r) for r in await cursor.fetchall()]

    return {
        "total_searches": total,
        "unique_queries": unique,
        "avg_listings_per_search": round(avg_listings, 1),
        "avg_response_ms": round(avg_response, 0),
        "by_query_type": type_breakdown,
    }


# ─── Price Snapshots ─────────────────────────────────────────────────


async def record_price_snapshot(
    query: str,
    source: str,
    title: str,
    price: float,
    part_number: str = None,
    brand: str = None,
    shipping_cost: float = 0,
    condition: str = None,
    url: str = None,
) -> int:
    """Record a price observation. Returns the row ID."""
    if price <= 0:
        return 0  # Don't record zero/invalid prices
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO price_snapshots
           (query, source, part_number, brand, title, price, shipping_cost,
            condition, url, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            query,
            source,
            part_number,
            brand,
            title,
            price,
            shipping_cost,
            condition,
            url,
            datetime.now(UTC).isoformat(),
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def record_price_snapshots_bulk(snapshots: list[dict]) -> int:
    """Record multiple price observations at once. Returns count recorded."""
    db = await get_db()
    count = 0
    for s in snapshots:
        if s.get("price", 0) <= 0:
            continue
        await db.execute(
            """INSERT INTO price_snapshots
               (query, source, part_number, brand, title, price, shipping_cost,
                condition, url, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                s.get("query", ""),
                s.get("source", ""),
                s.get("part_number"),
                s.get("brand"),
                s.get("title", ""),
                s["price"],
                s.get("shipping_cost", 0),
                s.get("condition"),
                s.get("url"),
                datetime.now(UTC).isoformat(),
            ),
        )
        count += 1
    await db.commit()
    return count


async def get_price_history(
    part_number: str = None,
    brand: str = None,
    source: str = None,
    limit: int = 50,
) -> list[dict]:
    """Get price history for a part, optionally filtered by brand/source."""
    db = await get_db()
    conditions = []
    params = []

    if part_number:
        conditions.append("part_number = ?")
        params.append(part_number.upper())
    if brand:
        conditions.append("brand = ?")
        params.append(brand)
    if source:
        conditions.append("source = ?")
        params.append(source)

    where = " AND ".join(conditions) if conditions else "1=1"
    cursor = await db.execute(
        f"SELECT * FROM price_snapshots WHERE {where} ORDER BY created_at DESC LIMIT ?",
        (*params, limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_price_trends(part_number: str, days: int = 30) -> list[dict]:
    """Get daily average price for a part number over the last N days."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT date(created_at) as date,
                  source,
                  AVG(price) as avg_price,
                  MIN(price) as min_price,
                  MAX(price) as max_price,
                  COUNT(*) as observations
           FROM price_snapshots
           WHERE part_number = ?
             AND created_at > datetime('now', ?)
           GROUP BY date(created_at), source
           ORDER BY date ASC""",
        (part_number.upper(), f"-{days} days"),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# ─── User Preferences ────────────────────────────────────────────────


async def get_preference(key: str, default: str = None) -> str | None:
    """Get a user preference value."""
    db = await get_db()
    cursor = await db.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row[0] if row else default


async def set_preference(key: str, value: str):
    """Set a user preference value."""
    db = await get_db()
    await db.execute(
        """INSERT INTO user_preferences (key, value, updated_at)
           VALUES (?, ?, datetime('now'))
           ON CONFLICT(key) DO UPDATE SET value=?, updated_at=datetime('now')""",
        (key, value, value),
    )
    await db.commit()
