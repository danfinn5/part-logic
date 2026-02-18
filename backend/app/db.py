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

        -- Canonical vehicles (A)
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            generation TEXT,
            submodel TEXT,
            trim TEXT,
            body_style TEXT,
            market TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_vehicles_make_model ON vehicles(make, model);
        CREATE INDEX IF NOT EXISTS idx_vehicles_year ON vehicles(year);

        -- Vehicle configs / trim-level detail (B)
        CREATE TABLE IF NOT EXISTS vehicle_configs (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL REFERENCES vehicles(vehicle_id),
            engine_code TEXT,
            engine_displacement_l REAL,
            aspiration TEXT,
            transmission_code TEXT,
            drivetrain TEXT,
            doors INTEGER,
            vin_pattern TEXT,
            build_date_start TEXT,
            build_date_end TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_vehicle_configs_vehicle ON vehicle_configs(vehicle_id);

        -- Vehicle aliases for backward compat + ingestion (C)
        CREATE TABLE IF NOT EXISTS vehicle_aliases (
            alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_text TEXT NOT NULL,
            alias_norm TEXT NOT NULL,
            year INTEGER,
            make_raw TEXT,
            model_raw TEXT,
            trim_raw TEXT,
            vehicle_id INTEGER REFERENCES vehicles(vehicle_id),
            config_id INTEGER REFERENCES vehicle_configs(config_id),
            source_domain TEXT,
            confidence INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_vehicle_aliases_norm_source
            ON vehicle_aliases(alias_norm, source_domain);
        CREATE INDEX IF NOT EXISTS idx_vehicle_aliases_vehicle ON vehicle_aliases(vehicle_id);
        CREATE INDEX IF NOT EXISTS idx_vehicle_aliases_unlinked ON vehicle_aliases(vehicle_id) WHERE vehicle_id IS NULL;

        -- Canonical parts (D)
        CREATE TABLE IF NOT EXISTS parts (
            part_id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_type TEXT NOT NULL CHECK(part_type IN ('oem','aftermarket','used','universal')),
            brand TEXT,
            name TEXT,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_parts_type_brand ON parts(part_type, brand);

        -- Part numbers / SKU namespace (E)
        CREATE TABLE IF NOT EXISTS part_numbers (
            pn_id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_id INTEGER NOT NULL REFERENCES parts(part_id),
            namespace TEXT NOT NULL,
            value TEXT NOT NULL,
            value_norm TEXT NOT NULL,
            source_domain TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_part_numbers_ns_value ON part_numbers(namespace, value_norm);
        CREATE INDEX IF NOT EXISTS idx_part_numbers_part ON part_numbers(part_id);
        CREATE INDEX IF NOT EXISTS idx_part_numbers_value_norm ON part_numbers(value_norm);

        -- Supersessions (F)
        CREATE TABLE IF NOT EXISTS supersessions (
            supersession_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_pn_id INTEGER NOT NULL REFERENCES part_numbers(pn_id),
            to_pn_id INTEGER NOT NULL REFERENCES part_numbers(pn_id),
            effective_date TEXT,
            notes TEXT,
            source_domain TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_supersessions_from ON supersessions(from_pn_id);
        CREATE INDEX IF NOT EXISTS idx_supersessions_to ON supersessions(to_pn_id);

        -- Interchange groups (G)
        CREATE TABLE IF NOT EXISTS interchange_groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_type TEXT NOT NULL,
            source_domain TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_interchange_groups_type ON interchange_groups(group_type);

        -- Interchange members (H)
        CREATE TABLE IF NOT EXISTS interchange_members (
            group_id INTEGER NOT NULL REFERENCES interchange_groups(group_id),
            pn_id INTEGER NOT NULL REFERENCES part_numbers(pn_id),
            PRIMARY KEY (group_id, pn_id)
        );
        CREATE INDEX IF NOT EXISTS idx_interchange_members_pn ON interchange_members(pn_id);

        -- Kits (I)
        CREATE TABLE IF NOT EXISTS kits (
            kit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            kit_part_id INTEGER NOT NULL REFERENCES parts(part_id),
            component_part_id INTEGER NOT NULL REFERENCES parts(part_id),
            qty REAL,
            notes TEXT,
            source_domain TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_kits_kit ON kits(kit_part_id);
        CREATE INDEX IF NOT EXISTS idx_kits_component ON kits(component_part_id);

        -- Fitments (J)
        CREATE TABLE IF NOT EXISTS fitments (
            fitment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_id INTEGER NOT NULL REFERENCES parts(part_id),
            vehicle_id INTEGER REFERENCES vehicles(vehicle_id),
            config_id INTEGER REFERENCES vehicle_configs(config_id),
            position TEXT,
            qualifiers_json TEXT,
            vin_range_start TEXT,
            vin_range_end TEXT,
            build_date_start TEXT,
            build_date_end TEXT,
            confidence INTEGER DEFAULT 100,
            source_domain TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_fitments_part ON fitments(part_id);
        CREATE INDEX IF NOT EXISTS idx_fitments_vehicle ON fitments(vehicle_id);
        CREATE INDEX IF NOT EXISTS idx_fitments_config ON fitments(config_id);
        CREATE INDEX IF NOT EXISTS idx_fitments_source ON fitments(source_domain);

        -- Saved searches (Phase 6F)
        CREATE TABLE IF NOT EXISTS saved_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            normalized_query TEXT NOT NULL,
            vehicle_make TEXT,
            vehicle_model TEXT,
            vehicle_year TEXT,
            vin TEXT,
            sort TEXT DEFAULT 'value',
            price_threshold REAL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_saved_searches_query ON saved_searches(normalized_query);
        CREATE INDEX IF NOT EXISTS idx_saved_searches_active ON saved_searches(is_active);

        -- Price alerts (Phase 6F)
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            saved_search_id INTEGER REFERENCES saved_searches(id) ON DELETE CASCADE,
            part_number TEXT,
            brand TEXT,
            target_price REAL NOT NULL,
            current_lowest REAL,
            triggered INTEGER DEFAULT 0,
            triggered_at TEXT,
            source TEXT,
            url TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_price_alerts_search ON price_alerts(saved_search_id);
        CREATE INDEX IF NOT EXISTS idx_price_alerts_active ON price_alerts(triggered) WHERE triggered = 0;
    """)
    await db.commit()
    await _migrate_search_history_vehicle_columns(db)


async def _migrate_search_history_vehicle_columns(db: aiosqlite.Connection) -> None:
    """Add vehicle_id and config_id to search_history if missing (backward compat)."""
    cursor = await db.execute("PRAGMA table_info(search_history)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "vehicle_id" not in columns:
        await db.execute("ALTER TABLE search_history ADD COLUMN vehicle_id INTEGER REFERENCES vehicles(vehicle_id)")
    if "config_id" not in columns:
        await db.execute(
            "ALTER TABLE search_history ADD COLUMN config_id INTEGER REFERENCES vehicle_configs(config_id)"
        )
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
    vehicle_id: int = None,
    config_id: int = None,
) -> int:
    """Record a search in history. Returns the row ID. vehicle_id/config_id from resolver when alias resolved."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO search_history
           (query, normalized_query, query_type, vehicle_hint, part_description,
            sort, market_listing_count, salvage_hit_count, external_link_count,
            source_count, has_interchange, cached, response_time_ms, vehicle_id, config_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            vehicle_id,
            config_id,
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


# ─── Saved Searches ─────────────────────────────────────────────────


async def save_search(
    query: str,
    normalized_query: str,
    vehicle_make: str = None,
    vehicle_model: str = None,
    vehicle_year: str = None,
    vin: str = None,
    sort: str = "value",
    price_threshold: float = None,
) -> int:
    """Save a search. Returns the row ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO saved_searches
           (query, normalized_query, vehicle_make, vehicle_model, vehicle_year,
            vin, sort, price_threshold, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))""",
        (query, normalized_query, vehicle_make, vehicle_model, vehicle_year, vin, sort, price_threshold),
    )
    await db.commit()
    return cursor.lastrowid


async def get_saved_searches(active_only: bool = True) -> list[dict]:
    """Get saved searches."""
    db = await get_db()
    if active_only:
        cursor = await db.execute("SELECT * FROM saved_searches WHERE is_active = 1 ORDER BY created_at DESC")
    else:
        cursor = await db.execute("SELECT * FROM saved_searches ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def delete_saved_search(search_id: int) -> bool:
    """Delete a saved search and its alerts. Returns True if found."""
    db = await get_db()
    cursor = await db.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
    await db.commit()
    return cursor.rowcount > 0


# ─── Price Alerts ────────────────────────────────────────────────────


async def create_price_alert(
    saved_search_id: int,
    target_price: float,
    part_number: str = None,
    brand: str = None,
) -> int:
    """Create a price alert. Returns the row ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO price_alerts
           (saved_search_id, part_number, brand, target_price, created_at)
           VALUES (?, ?, ?, ?, datetime('now'))""",
        (saved_search_id, part_number, brand, target_price),
    )
    await db.commit()
    return cursor.lastrowid


async def get_pending_alerts() -> list[dict]:
    """Get all untriggered price alerts."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT pa.*, ss.query, ss.normalized_query
           FROM price_alerts pa
           JOIN saved_searches ss ON pa.saved_search_id = ss.id
           WHERE pa.triggered = 0 AND ss.is_active = 1
           ORDER BY pa.created_at DESC"""
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_alerts_for_search(saved_search_id: int) -> list[dict]:
    """Get alerts for a specific saved search."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM price_alerts WHERE saved_search_id = ? ORDER BY created_at DESC",
        (saved_search_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def trigger_alert(
    alert_id: int,
    current_lowest: float,
    source: str = None,
    url: str = None,
) -> bool:
    """Mark an alert as triggered. Returns True if updated."""
    db = await get_db()
    cursor = await db.execute(
        """UPDATE price_alerts
           SET triggered = 1, triggered_at = datetime('now'),
               current_lowest = ?, source = ?, url = ?
           WHERE id = ? AND triggered = 0""",
        (current_lowest, source, url, alert_id),
    )
    await db.commit()
    return cursor.rowcount > 0
