"""
Knowledge learning loop — persists AI analysis back to the canonical database.

After every AI-analyzed search, this service extracts structured knowledge
(part numbers, cross-references, brand quality data, vehicle fitment) and
writes it to the canonical tables. The system gets smarter with every query.
"""

import logging

from app.db import get_db
from app.services.ai_advisor import AIAdvisorResult
from app.utils.part_numbers import part_number_value_norm

logger = logging.getLogger(__name__)


async def persist_ai_knowledge(ai_result: AIAdvisorResult, query: str) -> dict:
    """
    Extract and persist knowledge from an AI advisor result.

    Returns a summary dict of what was persisted:
      {"vehicles": N, "parts": N, "part_numbers": N, "interchange": N}
    """
    if not ai_result or ai_result.error:
        return {"vehicles": 0, "parts": 0, "part_numbers": 0, "interchange": 0}

    db = await get_db()
    stats = {"vehicles": 0, "parts": 0, "part_numbers": 0, "interchange": 0}

    try:
        # --- Persist vehicle ---
        vehicle_id = None
        if ai_result.vehicle_make:
            vehicle_id = await _ensure_vehicle(
                db,
                make=ai_result.vehicle_make,
                model=ai_result.vehicle_model,
                generation=ai_result.vehicle_generation,
                years=ai_result.vehicle_years,
                stats=stats,
            )

        # --- Persist OEM part numbers ---
        oem_pn_ids = []
        for pn in ai_result.oem_part_numbers or []:
            pn_id = await _ensure_part_number(db, pn, namespace="oem", brand=ai_result.vehicle_make, stats=stats)
            if pn_id:
                oem_pn_ids.append(pn_id)

        # --- Persist recommendations (aftermarket parts + cross-references) ---
        rec_pn_ids = []
        for rec in ai_result.recommendations or []:
            if not rec.part_number:
                continue
            pn_id = await _ensure_part_number(
                db,
                rec.part_number,
                namespace="manufacturer",
                brand=rec.brand,
                name=rec.title,
                quality_tier=rec.quality_tier,
                stats=stats,
            )
            if pn_id:
                rec_pn_ids.append(pn_id)

        # --- Create interchange group if we have OEM + aftermarket PNs ---
        all_pn_ids = oem_pn_ids + rec_pn_ids
        if len(all_pn_ids) >= 2:
            await _ensure_interchange_group(db, all_pn_ids, query, stats)

        # --- Link fitments if we have a vehicle and part numbers ---
        if vehicle_id and all_pn_ids:
            await _ensure_fitments(db, all_pn_ids, vehicle_id, stats)

        await db.commit()

    except Exception as e:
        logger.warning(f"Knowledge persistence failed: {e}")
        return stats

    if any(v > 0 for v in stats.values()):
        logger.info(
            f"Knowledge persisted: {stats['vehicles']} vehicles, "
            f"{stats['parts']} parts, {stats['part_numbers']} PNs, "
            f"{stats['interchange']} interchange links"
        )

    return stats


async def _ensure_vehicle(db, make, model, generation, years, stats) -> int | None:
    """Find or create a vehicle record. Returns vehicle_id."""
    make = make.strip()
    model = (model or "").strip()
    if not make:
        return None

    # Parse year range like "1998-2006" — use the midpoint or first year
    year = None
    if years:
        try:
            parts = years.split("-")
            year = int(parts[0].strip())
        except (ValueError, IndexError):
            pass

    # Check if vehicle exists
    cursor = await db.execute(
        """SELECT vehicle_id FROM vehicles
           WHERE LOWER(TRIM(make)) = LOWER(?)
             AND LOWER(TRIM(model)) = LOWER(?)
             AND (? IS NULL OR year = ?)
           LIMIT 1""",
        (make, model, year, year),
    )
    row = await cursor.fetchone()
    if row:
        return row[0]

    # Create vehicle
    cursor = await db.execute(
        """INSERT INTO vehicles (year, make, model, generation, created_at, updated_at)
           VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
        (year or 0, make, model or "Unknown", generation),
    )
    stats["vehicles"] += 1
    return cursor.lastrowid


async def _ensure_part_number(
    db, part_number, namespace, brand=None, name=None, quality_tier=None, stats=None
) -> int | None:
    """Find or create a part_number record. Returns pn_id."""
    if not part_number or len(part_number.strip()) < 2:
        return None

    pn_norm = part_number_value_norm(part_number)

    # Check if part_number already exists
    cursor = await db.execute(
        "SELECT pn_id FROM part_numbers WHERE value_norm = ? LIMIT 1",
        (pn_norm,),
    )
    row = await cursor.fetchone()
    if row:
        return row[0]

    # Determine part type
    part_type = "oem" if namespace == "oem" else "aftermarket"

    # Create the part first
    cursor = await db.execute(
        """INSERT INTO parts (part_type, brand, name, description, created_at, updated_at)
           VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
        (part_type, brand, name or part_number, quality_tier),
    )
    part_id = cursor.lastrowid
    if stats:
        stats["parts"] += 1

    # Create the part_number
    cursor = await db.execute(
        """INSERT OR IGNORE INTO part_numbers (part_id, namespace, value, value_norm, source_domain, created_at)
           VALUES (?, ?, ?, ?, 'ai_advisor', datetime('now'))""",
        (part_id, namespace, part_number, pn_norm),
    )
    if stats:
        stats["part_numbers"] += 1

    return cursor.lastrowid if cursor.lastrowid else None


async def _ensure_interchange_group(db, pn_ids, query, stats):
    """Create an interchange group linking related part numbers."""
    if len(pn_ids) < 2:
        return

    # Check if these PNs are already in a group together
    placeholders = ",".join("?" * len(pn_ids))
    cursor = await db.execute(
        f"""SELECT group_id, COUNT(*) as cnt
            FROM interchange_members
            WHERE pn_id IN ({placeholders})
            GROUP BY group_id
            HAVING cnt >= 2
            LIMIT 1""",
        pn_ids,
    )
    row = await cursor.fetchone()
    if row:
        group_id = row[0]
    else:
        # Create new group
        cursor = await db.execute(
            """INSERT INTO interchange_groups (group_type, source_domain, notes, created_at, updated_at)
               VALUES ('cross_reference', 'ai_advisor', ?, datetime('now'), datetime('now'))""",
            (f"From query: {query[:100]}",),
        )
        group_id = cursor.lastrowid

    # Add members that aren't already in the group
    for pn_id in pn_ids:
        await db.execute(
            "INSERT OR IGNORE INTO interchange_members (group_id, pn_id) VALUES (?, ?)",
            (group_id, pn_id),
        )
        stats["interchange"] += 1


async def _ensure_fitments(db, pn_ids, vehicle_id, stats):
    """Link part numbers to a vehicle via fitments."""
    for pn_id in pn_ids:
        # Get the part_id for this pn_id
        cursor = await db.execute("SELECT part_id FROM part_numbers WHERE pn_id = ?", (pn_id,))
        row = await cursor.fetchone()
        if not row:
            continue
        part_id = row[0]

        # Check if fitment already exists
        cursor = await db.execute(
            "SELECT fitment_id FROM fitments WHERE part_id = ? AND vehicle_id = ? LIMIT 1",
            (part_id, vehicle_id),
        )
        if not await cursor.fetchone():
            await db.execute(
                """INSERT INTO fitments (part_id, vehicle_id, confidence, source_domain, created_at, updated_at)
                   VALUES (?, ?, 70, 'ai_advisor', datetime('now'), datetime('now'))""",
                (part_id, vehicle_id),
            )


async def get_known_part_numbers(query_part_numbers: list[str]) -> list[dict]:
    """
    Look up what we already know about a set of part numbers from the knowledge DB.
    Returns enriched data: interchange numbers, brands, fitment vehicles.
    """
    if not query_part_numbers:
        return []

    db = await get_db()
    results = []

    for pn in query_part_numbers:
        pn_norm = part_number_value_norm(pn)

        # Get the part and its group
        cursor = await db.execute(
            """SELECT pn.pn_id, pn.part_id, pn.namespace, p.brand, p.name, p.part_type, p.description
               FROM part_numbers pn
               JOIN parts p ON pn.part_id = p.part_id
               WHERE pn.value_norm = ?
               LIMIT 1""",
            (pn_norm,),
        )
        row = await cursor.fetchone()
        if not row:
            continue

        pn_id, part_id = row[0], row[1]
        entry = {
            "part_number": pn,
            "brand": row[3],
            "name": row[4],
            "part_type": row[5],
            "quality_tier": row[6],
            "interchange": [],
            "fits_vehicles": [],
        }

        # Get interchange numbers
        cursor = await db.execute(
            """SELECT pn2.value, p2.brand, p2.name
               FROM interchange_members im1
               JOIN interchange_members im2 ON im1.group_id = im2.group_id AND im1.pn_id != im2.pn_id
               JOIN part_numbers pn2 ON im2.pn_id = pn2.pn_id
               JOIN parts p2 ON pn2.part_id = p2.part_id
               WHERE im1.pn_id = ?""",
            (pn_id,),
        )
        for irow in await cursor.fetchall():
            entry["interchange"].append(
                {
                    "part_number": irow[0],
                    "brand": irow[1],
                    "name": irow[2],
                }
            )

        # Get fitted vehicles
        cursor = await db.execute(
            """SELECT v.year, v.make, v.model, v.generation, f.confidence
               FROM fitments f
               JOIN vehicles v ON f.vehicle_id = v.vehicle_id
               WHERE f.part_id = ?
               ORDER BY f.confidence DESC
               LIMIT 10""",
            (part_id,),
        )
        for frow in await cursor.fetchall():
            entry["fits_vehicles"].append(
                {
                    "year": frow[0],
                    "make": frow[1],
                    "model": frow[2],
                    "generation": frow[3],
                    "confidence": frow[4],
                }
            )

        results.append(entry)

    return results
