"""
Resolve loose vehicle strings to canonical vehicle_id / config_id.

- First try exact alias_norm match already linked.
- Else parse for year + make + model and fuzzy match against known vehicles.
- Create/update vehicle_aliases with confidence; link when >= threshold.
- Never delete or overwrite raw strings; store provenance and confidence.
"""

import logging
from dataclasses import dataclass

from app.db import get_db
from app.utils.vehicle_normalizer import normalize_vehicle_string, parse_vehicle_loose

logger = logging.getLogger(__name__)

# Minimum confidence to auto-link alias to a vehicle (0-100)
LINK_THRESHOLD = 85


@dataclass
class ResolveResult:
    vehicle_id: int | None
    config_id: int | None
    confidence: int
    parsed_year: int | None
    parsed_make: str | None
    parsed_model: str | None
    alias_id: int | None
    created_alias: bool


async def resolve_vehicle_alias(
    alias_text: str,
    source_domain: str | None = None,
) -> ResolveResult:
    """
    Resolve a loose vehicle string to canonical vehicle_id/config_id.

    1. Normalize and look up existing alias_norm (+ source_domain) already linked.
    2. Else parse year/make/model and try to match existing vehicles.
    3. Create or update vehicle_aliases record with confidence.
    4. If confidence >= LINK_THRESHOLD, link to vehicles (create vehicle if needed).
    """
    if not alias_text or not alias_text.strip():
        return ResolveResult(
            vehicle_id=None,
            config_id=None,
            confidence=0,
            parsed_year=None,
            parsed_make=None,
            parsed_model=None,
            alias_id=None,
            created_alias=False,
        )

    alias_norm = normalize_vehicle_string(alias_text)
    parsed = parse_vehicle_loose(alias_text)
    db = await get_db()

    # 1) Exact alias_norm + source_domain already linked
    cursor = await db.execute(
        """SELECT alias_id, vehicle_id, config_id, confidence
           FROM vehicle_aliases
           WHERE alias_norm = ? AND (source_domain IS ? OR source_domain = ?)
           LIMIT 1""",
        (alias_norm, source_domain, source_domain or ""),
    )
    row = await cursor.fetchone()
    if row and row["vehicle_id"] is not None:
        return ResolveResult(
            vehicle_id=row["vehicle_id"],
            config_id=row["config_id"],
            confidence=row["confidence"] or 0,
            parsed_year=parsed.year,
            parsed_make=parsed.make_raw,
            parsed_model=parsed.model_raw,
            alias_id=row["alias_id"],
            created_alias=False,
        )

    # 2) Parse and try to match existing vehicles table
    vehicle_id: int | None = None
    config_id: int | None = None
    confidence = 0

    if parsed.year and parsed.make_raw:
        make_canon = parsed.make_raw.strip().lower()
        model_canon = (parsed.model_raw or "").strip().lower()
        cursor = await db.execute(
            """SELECT vehicle_id FROM vehicles
               WHERE year = ? AND LOWER(TRIM(make)) = ? AND LOWER(TRIM(model)) = ?
               LIMIT 1""",
            (parsed.year, make_canon, model_canon),
        )
        vrow = await cursor.fetchone()
        if vrow:
            vehicle_id = vrow["vehicle_id"]
            confidence = 90
        else:
            # No exact match: try create vehicle and alias
            confidence = _confidence_from_parsed(parsed)
            if confidence >= LINK_THRESHOLD:
                cursor = await db.execute(
                    """INSERT INTO vehicles (year, make, model, generation, submodel, trim, created_at, updated_at)
                       VALUES (?, ?, ?, NULL, NULL, ?, datetime('now'), datetime('now'))""",
                    (
                        parsed.year,
                        parsed.make_raw.strip().title(),
                        (parsed.model_raw or "").strip().title(),
                        parsed.trim_raw or "",
                    ),
                )
                await db.commit()
                vehicle_id = cursor.lastrowid
                logger.info("Created vehicle_id=%s for alias_norm=%s", vehicle_id, alias_norm)

    # 3) Upsert vehicle_aliases (preserve raw text, set link if confidence high enough)
    alias_id, created = await _upsert_alias(
        db=db,
        alias_text=alias_text.strip(),
        alias_norm=alias_norm,
        year=parsed.year,
        make_raw=parsed.make_raw,
        model_raw=parsed.model_raw,
        trim_raw=parsed.trim_raw,
        vehicle_id=vehicle_id if confidence >= LINK_THRESHOLD else None,
        config_id=config_id,
        source_domain=source_domain,
        confidence=confidence,
    )
    return ResolveResult(
        vehicle_id=vehicle_id if confidence >= LINK_THRESHOLD else None,
        config_id=config_id,
        confidence=confidence,
        parsed_year=parsed.year,
        parsed_make=parsed.make_raw,
        parsed_model=parsed.model_raw,
        alias_id=alias_id,
        created_alias=created,
    )


def _confidence_from_parsed(parsed) -> int:
    """Heuristic confidence 0-100 from parsed fields."""
    if not parsed.year or not parsed.make_raw:
        return 30
    if not parsed.model_raw:
        return 60
    return 85


async def _upsert_alias(
    db,
    alias_text: str,
    alias_norm: str,
    year: int | None,
    make_raw: str | None,
    model_raw: str | None,
    trim_raw: str | None,
    vehicle_id: int | None,
    config_id: int | None,
    source_domain: str | None,
    confidence: int,
) -> tuple[int | None, bool]:
    """Insert or update vehicle_aliases. Returns (alias_id, created)."""
    cursor = await db.execute(
        """SELECT alias_id FROM vehicle_aliases
           WHERE alias_norm = ? AND (source_domain IS ? OR source_domain = ?)
           LIMIT 1""",
        (alias_norm, source_domain, source_domain or ""),
    )
    row = await cursor.fetchone()
    if row:
        await db.execute(
            """UPDATE vehicle_aliases
               SET year=?, make_raw=?, model_raw=?, trim_raw=?, vehicle_id=?, config_id=?,
                   confidence=?, updated_at=datetime('now')
               WHERE alias_id=?""",
            (year, make_raw, model_raw, trim_raw, vehicle_id, config_id, confidence, row["alias_id"]),
        )
        await db.commit()
        return (row["alias_id"], False)
    cursor = await db.execute(
        """INSERT INTO vehicle_aliases
           (alias_text, alias_norm, year, make_raw, model_raw, trim_raw, vehicle_id, config_id,
            source_domain, confidence, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
        (
            alias_text,
            alias_norm,
            year,
            make_raw,
            model_raw,
            trim_raw,
            vehicle_id,
            config_id,
            source_domain,
            confidence,
        ),
    )
    await db.commit()
    return (cursor.lastrowid, True)


async def reconcile_unlinked_aliases(limit: int = 500, threshold: int = LINK_THRESHOLD) -> int:
    """
    Run resolver on unlinked aliases (vehicle_id IS NULL). Incremental.
    Returns count of aliases newly linked.
    """
    db = await get_db()
    cursor = await db.execute(
        """SELECT alias_id, alias_text, alias_norm, source_domain FROM vehicle_aliases
           WHERE vehicle_id IS NULL AND alias_norm != ''
           ORDER BY alias_id LIMIT ?""",
        (limit,),
    )
    rows = await cursor.fetchall()
    linked = 0
    for row in rows:
        result = await resolve_vehicle_alias(row["alias_text"], row["source_domain"])
        if result.vehicle_id is not None:
            linked += 1
    return linked
