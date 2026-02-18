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


async def ingest_fitment_from_listing(
    part_number: str,
    brand: str | None,
    fitment_vehicles: list[dict],
    source_domain: str = "fcpeuro.com",
) -> int:
    """
    Ingest fitment data from a listing. fitment_vehicles is a list of
    dicts with keys: year, make, model. Creates parts/part_numbers if needed
    and links fitments. Returns number of fitments created.
    """
    db = await get_db()
    pn_norm = part_number_value_norm(part_number)

    # Find or create part_number
    cursor = await db.execute("SELECT pn_id, part_id FROM part_numbers WHERE value_norm = ? LIMIT 1", (pn_norm,))
    row = await cursor.fetchone()

    if row:
        part_id = row[1]
    else:
        # Create part
        part_type = (
            "oem" if brand and brand.upper() in ("BMW", "PORSCHE", "VOLVO", "AUDI", "VW", "MERCEDES") else "aftermarket"
        )
        cursor = await db.execute(
            """INSERT INTO parts (part_type, brand, name, created_at, updated_at)
               VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
            (part_type, brand, part_number),
        )
        part_id = cursor.lastrowid
        # Create part_number
        await db.execute(
            """INSERT OR IGNORE INTO part_numbers (part_id, namespace, value, value_norm, source_domain, created_at)
               VALUES (?, 'manufacturer', ?, ?, ?, datetime('now'))""",
            (part_id, part_number, pn_norm, source_domain),
        )

    count = 0
    for v in fitment_vehicles:
        year = v.get("year")
        make = v.get("make")
        model = v.get("model")
        if not (year and make and model):
            continue

        # Find or create vehicle
        cursor = await db.execute(
            "SELECT vehicle_id FROM vehicles WHERE year = ? AND LOWER(TRIM(make)) = LOWER(?) AND LOWER(TRIM(model)) = LOWER(?) LIMIT 1",
            (year, make.strip(), model.strip()),
        )
        vrow = await cursor.fetchone()
        if vrow:
            vehicle_id = vrow[0]
        else:
            cursor = await db.execute(
                """INSERT INTO vehicles (year, make, model, created_at, updated_at)
                   VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                (year, make.strip(), model.strip()),
            )
            vehicle_id = cursor.lastrowid

        # Check if fitment already exists
        cursor = await db.execute(
            "SELECT fitment_id FROM fitments WHERE part_id = ? AND vehicle_id = ? LIMIT 1",
            (part_id, vehicle_id),
        )
        if not await cursor.fetchone():
            await db.execute(
                """INSERT INTO fitments (part_id, vehicle_id, confidence, source_domain, created_at, updated_at)
                   VALUES (?, ?, 80, ?, datetime('now'), datetime('now'))""",
                (part_id, vehicle_id, source_domain),
            )
            count += 1

    await db.commit()
    return count


async def get_fitments_for_part_numbers(part_numbers: list[str], vehicle_id: int) -> dict[str, str]:
    """
    Check fitments for a list of part numbers against a specific vehicle.
    Returns dict of part_number -> fitment_status ('confirmed_fit', 'likely_fit', 'unknown').
    """
    db = await get_db()
    result: dict[str, str] = {}

    for pn in part_numbers:
        pn_norm = part_number_value_norm(pn)
        cursor = await db.execute(
            """SELECT f.confidence
               FROM fitments f
               JOIN part_numbers pn ON f.part_id = pn.part_id
               WHERE pn.value_norm = ? AND f.vehicle_id = ?
               LIMIT 1""",
            (pn_norm, vehicle_id),
        )
        row = await cursor.fetchone()
        if row:
            confidence = row[0] or 0
            result[pn] = "confirmed_fit" if confidence >= 80 else "likely_fit"

    return result
