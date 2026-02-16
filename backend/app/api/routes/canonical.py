"""
Admin/debug API for canonical data: vehicle aliases, part numbers, fitment inspector.
"""

import json
import logging

from fastapi import APIRouter, Query

from app.db import get_db
from app.utils.part_numbers import part_number_value_norm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/canonical", tags=["canonical"])


@router.get("/aliases")
async def list_vehicle_aliases(
    unlinked_only: bool = Query(False, description="Only aliases with vehicle_id IS NULL"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List vehicle aliases with optional unlinked filter. For admin UI."""
    db = await get_db()
    if unlinked_only:
        cursor = await db.execute(
            """SELECT alias_id, alias_text, alias_norm, year, make_raw, model_raw, trim_raw,
                      vehicle_id, config_id, source_domain, confidence, created_at
               FROM vehicle_aliases WHERE vehicle_id IS NULL ORDER BY alias_id LIMIT ? OFFSET ?""",
            (limit, offset),
        )
    else:
        cursor = await db.execute(
            """SELECT alias_id, alias_text, alias_norm, year, make_raw, model_raw, trim_raw,
                      vehicle_id, config_id, source_domain, confidence, created_at
               FROM vehicle_aliases ORDER BY alias_id LIMIT ? OFFSET ?""",
            (limit, offset),
        )
    rows = await cursor.fetchall()
    return {"aliases": [dict(r) for r in rows]}


@router.patch("/aliases/{alias_id}/link")
async def link_alias_to_vehicle(
    alias_id: int,
    vehicle_id: int,
    config_id: int | None = None,
):
    """Manually link an alias to a canonical vehicle (and optional config)."""
    db = await get_db()
    await db.execute(
        "UPDATE vehicle_aliases SET vehicle_id=?, config_id=?, updated_at=datetime('now') WHERE alias_id=?",
        (vehicle_id, config_id, alias_id),
    )
    await db.commit()
    return {"alias_id": alias_id, "vehicle_id": vehicle_id, "config_id": config_id}


@router.get("/part_numbers")
async def search_part_numbers(
    namespace: str | None = Query(None),
    value_norm: str | None = Query(None, description="Normalized value or raw (will be normalized)"),
    limit: int = Query(50, ge=1, le=200),
):
    """Search part_numbers by namespace and/or value_norm. Returns rows with part info."""
    db = await get_db()
    params = []
    sql = """SELECT pn.pn_id, pn.part_id, pn.namespace, pn.value, pn.value_norm, pn.source_domain,
                    p.part_type, p.brand, p.name
             FROM part_numbers pn
             JOIN parts p ON p.part_id = pn.part_id WHERE 1=1"""
    if namespace:
        sql += " AND pn.namespace = ?"
        params.append(namespace)
    if value_norm:
        vn = part_number_value_norm(value_norm)
        sql += " AND pn.value_norm LIKE ?"
        params.append(f"%{vn}%")
    sql += " ORDER BY pn.pn_id LIMIT ?"
    params.append(limit)
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    return {"part_numbers": [dict(r) for r in rows]}


@router.get("/fitments")
async def fitment_inspector(
    year: int | None = Query(None),
    make: str | None = Query(None),
    model: str | None = Query(None),
    part_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Given year/make/model (or part_id), return matching fitments with qualifiers and provenance.
    Explains why a part matches (qualifiers + source).
    """
    db = await get_db()
    params = []
    sql = """SELECT f.fitment_id, f.part_id, f.vehicle_id, f.config_id, f.position, f.qualifiers_json,
                    f.vin_range_start, f.vin_range_end, f.build_date_start, f.build_date_end,
                    f.confidence, f.source_domain,
                    v.year, v.make, v.model, v.generation,
                    p.part_type, p.brand, p.name
             FROM fitments f
             LEFT JOIN vehicles v ON v.vehicle_id = f.vehicle_id
             JOIN parts p ON p.part_id = f.part_id WHERE 1=1"""
    if year is not None:
        sql += " AND v.year = ?"
        params.append(year)
    if make:
        sql += " AND LOWER(TRIM(v.make)) = LOWER(?)"
        params.append(make.strip())
    if model:
        sql += " AND LOWER(TRIM(v.model)) = LOWER(?)"
        params.append(model.strip())
    if part_id is not None:
        sql += " AND f.part_id = ?"
        params.append(part_id)
    sql += " ORDER BY f.fitment_id LIMIT ?"
    params.append(limit)
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d.get("qualifiers_json"):
            try:
                d["qualifiers"] = json.loads(d["qualifiers_json"])
            except Exception:
                d["qualifiers"] = None
        out.append(d)
    return {"fitments": out}


@router.get("/vehicles")
async def list_vehicles(
    make: str | None = Query(None),
    year: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List canonical vehicles for admin (e.g. when manually linking aliases)."""
    db = await get_db()
    params = []
    sql = "SELECT vehicle_id, year, make, model, generation, submodel, trim, body_style, market FROM vehicles WHERE 1=1"
    if make:
        sql += " AND LOWER(TRIM(make)) = LOWER(?)"
        params.append(make.strip())
    if year is not None:
        sql += " AND year = ?"
        params.append(year)
    sql += " ORDER BY year DESC, make, model LIMIT ?"
    params.append(limit)
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    return {"vehicles": [dict(r) for r in rows]}
