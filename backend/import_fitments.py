#!/usr/bin/env python3
"""
Import fitments from CSV. part_id and vehicle_id must already exist.

Usage:
    python import_fitments.py --file data/templates/fitments_template.csv
    CSV: part_id, vehicle_id, config_id, position, qualifiers_json, vin_range_start, vin_range_end, build_date_start, build_date_end, confidence, source_domain
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db_canonical import insert_fitment


async def run(filepath: str) -> int:
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {path}")
        return 0
    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            part_id = int(row["part_id"])
            vehicle_id = row.get("vehicle_id", "").strip()
            vehicle_id = int(vehicle_id) if vehicle_id.isdigit() else None
            config_id = row.get("config_id", "").strip()
            config_id = int(config_id) if config_id.isdigit() else None
            position = row.get("position", "").strip() or None
            qualifiers_json = row.get("qualifiers_json", "").strip() or None
            vin_start = row.get("vin_range_start", "").strip() or None
            vin_end = row.get("vin_range_end", "").strip() or None
            build_start = row.get("build_date_start", "").strip() or None
            build_end = row.get("build_date_end", "").strip() or None
            confidence = int(row.get("confidence", 100))
            source_domain = row.get("source_domain", "").strip() or None
            fid = await insert_fitment(
                part_id=part_id,
                vehicle_id=vehicle_id,
                config_id=config_id,
                position=position,
                qualifiers_json=qualifiers_json,
                vin_range_start=vin_start,
                vin_range_end=vin_end,
                build_date_start=build_start,
                build_date_end=build_end,
                confidence=confidence,
                source_domain=source_domain,
            )
            count += 1
            print(f"  + fitment_id={fid} part_id={part_id} vehicle_id={vehicle_id}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Import fitments from CSV")
    parser.add_argument("--file", required=True, help="Path to CSV")
    args = parser.parse_args()
    n = asyncio.run(run(args.file))
    print(f"Imported {n} fitments.")


if __name__ == "__main__":
    main()
