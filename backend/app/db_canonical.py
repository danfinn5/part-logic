"""
Canonical data layer: vehicles, vehicle_configs, vehicle_aliases, parts, part_numbers, fitments, etc.
Used by import CLIs and vehicle resolver.
"""

from app.db import get_db
from app.utils.part_numbers import part_number_value_norm


async def insert_vehicle(
    year: int,
    make: str,
    model: str,
    generation: str | None = None,
    submodel: str | None = None,
    trim: str | None = None,
    body_style: str | None = None,
    market: str | None = None,
) -> int:
    """Insert a canonical vehicle. Returns vehicle_id."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO vehicles (year, make, model, generation, submodel, trim, body_style, market, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
        (year, make, model, generation, submodel, trim, body_style, market),
    )
    await db.commit()
    return cursor.lastrowid


async def insert_vehicle_alias(
    alias_text: str,
    alias_norm: str,
    year: int | None = None,
    make_raw: str | None = None,
    model_raw: str | None = None,
    trim_raw: str | None = None,
    vehicle_id: int | None = None,
    config_id: int | None = None,
    source_domain: str | None = None,
    confidence: int = 0,
) -> int:
    """Insert vehicle_aliases row. Returns alias_id."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO vehicle_aliases
           (alias_text, alias_norm, year, make_raw, model_raw, trim_raw, vehicle_id, config_id, source_domain, confidence, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
        (alias_text, alias_norm, year, make_raw, model_raw, trim_raw, vehicle_id, config_id, source_domain, confidence),
    )
    await db.commit()
    return cursor.lastrowid


async def insert_part(
    part_type: str,
    brand: str | None = None,
    name: str | None = None,
    description: str | None = None,
) -> int:
    """Insert canonical part. part_type: oem|aftermarket|used|universal. Returns part_id."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO parts (part_type, brand, name, description, created_at, updated_at)
           VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
        (part_type, brand, name, description),
    )
    await db.commit()
    return cursor.lastrowid


async def insert_part_number(
    part_id: int,
    namespace: str,
    value: str,
    value_norm: str | None = None,
    source_domain: str | None = None,
) -> int:
    """Insert part_numbers row. value_norm defaults from value (uppercase, no spaces/dashes). Returns pn_id."""
    if value_norm is None:
        value_norm = part_number_value_norm(value)
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO part_numbers (part_id, namespace, value, value_norm, source_domain, created_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))""",
        (part_id, namespace, value, value_norm, source_domain),
    )
    await db.commit()
    return cursor.lastrowid


async def insert_fitment(
    part_id: int,
    vehicle_id: int | None = None,
    config_id: int | None = None,
    position: str | None = None,
    qualifiers_json: str | None = None,
    vin_range_start: str | None = None,
    vin_range_end: str | None = None,
    build_date_start: str | None = None,
    build_date_end: str | None = None,
    confidence: int = 100,
    source_domain: str | None = None,
) -> int:
    """Insert fitment. Returns fitment_id."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO fitments
           (part_id, vehicle_id, config_id, position, qualifiers_json, vin_range_start, vin_range_end,
            build_date_start, build_date_end, confidence, source_domain, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
        (
            part_id,
            vehicle_id,
            config_id,
            position,
            qualifiers_json,
            vin_range_start,
            vin_range_end,
            build_date_start,
            build_date_end,
            confidence,
            source_domain,
        ),
    )
    await db.commit()
    return cursor.lastrowid


async def get_vehicle_by_make_model_year(year: int, make: str, model: str) -> dict | None:
    """Fetch one vehicle by year, make, model (case-insensitive)."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM vehicles WHERE year = ? AND LOWER(TRIM(make)) = LOWER(?) AND LOWER(TRIM(model)) = LOWER(?)
           LIMIT 1""",
        (year, make.strip(), model.strip()),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_part_by_id(part_id: int) -> dict | None:
    """Fetch part by part_id."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM parts WHERE part_id = ?", (part_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_pn_by_namespace_value(namespace: str, value_norm: str) -> dict | None:
    """Fetch part_numbers row by namespace and value_norm."""
    db = await get_db()
    vn = part_number_value_norm(value_norm)
    cursor = await db.execute(
        "SELECT * FROM part_numbers WHERE namespace = ? AND value_norm = ? LIMIT 1", (namespace, vn)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None
