#!/usr/bin/env python3
"""
Import canonical vehicles from CSV.

Usage:
    python import_vehicles.py --file data/templates/vehicles_template.csv
    python import_vehicles.py --file data/vehicles.csv
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import get_db
from app.db_canonical import get_vehicle_by_make_model_year, insert_vehicle


async def run(filepath: str, upsert: bool) -> int:
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {path}")
        return 0
    await get_db()
    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row["year"])
            make = row["make"].strip()
            model = row["model"].strip()
            generation = row.get("generation", "").strip() or None
            submodel = row.get("submodel", "").strip() or None
            trim = row.get("trim", "").strip() or None
            body_style = row.get("body_style", "").strip() or None
            market = row.get("market", "").strip() or None
            if upsert:
                existing = await get_vehicle_by_make_model_year(year, make, model)
                if existing:
                    print(f"  skip (exists) {year} {make} {model}")
                    continue
            vid = await insert_vehicle(
                year=year,
                make=make,
                model=model,
                generation=generation,
                submodel=submodel,
                trim=trim,
                body_style=body_style,
                market=market,
            )
            count += 1
            print(f"  + vehicle_id={vid} {year} {make} {model}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Import vehicles from CSV")
    parser.add_argument(
        "--file", required=True, help="Path to CSV (year, make, model, generation, submodel, trim, body_style, market)"
    )
    parser.add_argument("--upsert", action="store_true", help="Skip rows that already exist (year+make+model)")
    args = parser.parse_args()
    n = asyncio.run(run(args.file, args.upsert))
    print(f"Imported {n} vehicles.")


if __name__ == "__main__":
    main()
