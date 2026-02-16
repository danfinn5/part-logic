#!/usr/bin/env python3
"""
Import vehicle aliases from CSV. Does not auto-resolve; use reconcile_aliases to link.

Usage:
    python import_aliases.py --file data/templates/aliases_template.csv
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import get_db
from app.utils.vehicle_normalizer import normalize_vehicle_string


async def run(filepath: str) -> int:
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {path}")
        return 0
    db = await get_db()
    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alias_text = row["alias_text"].strip()
            if not alias_text:
                continue
            alias_norm = normalize_vehicle_string(alias_text)
            source_domain = row.get("source_domain", "").strip() or None
            year = row.get("year", "").strip()
            year = int(year) if year.isdigit() else None
            make_raw = row.get("make_raw", "").strip() or None
            model_raw = row.get("model_raw", "").strip() or None
            trim_raw = row.get("trim_raw", "").strip() or None
            cursor = await db.execute(
                """INSERT INTO vehicle_aliases
                   (alias_text, alias_norm, year, make_raw, model_raw, trim_raw, vehicle_id, config_id, source_domain, confidence, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, 0, datetime('now'), datetime('now'))""",
                (alias_text, alias_norm, year, make_raw, model_raw, trim_raw, source_domain),
            )
            aid = cursor.lastrowid
            await db.commit()
            count += 1
            print(f"  + alias_id={aid} alias_norm={alias_norm[:50]}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Import vehicle aliases from CSV")
    parser.add_argument(
        "--file", required=True, help="Path to CSV (alias_text, source_domain, year, make_raw, model_raw, trim_raw)"
    )
    args = parser.parse_args()
    n = asyncio.run(run(args.file))
    print(f"Imported {n} aliases. Run reconcile_aliases to link to vehicles.")


if __name__ == "__main__":
    main()
