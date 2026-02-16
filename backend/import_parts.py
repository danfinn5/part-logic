#!/usr/bin/env python3
"""
Import canonical parts (and optional part_numbers) from CSV.

Usage:
    python import_parts.py --file data/templates/parts_template.csv
    CSV: part_type, brand, name, description
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db_canonical import insert_part

PART_TYPES = ("oem", "aftermarket", "used", "universal")


async def run(filepath: str) -> int:
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {path}")
        return 0
    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            part_type = row.get("part_type", "oem").strip().lower()
            if part_type not in PART_TYPES:
                part_type = "oem"
            brand = row.get("brand", "").strip() or None
            name = row.get("name", "").strip() or None
            description = row.get("description", "").strip() or None
            part_id = await insert_part(part_type=part_type, brand=brand, name=name, description=description)
            count += 1
            print(f"  + part_id={part_id} {part_type} {brand or ''} {name or ''}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Import parts from CSV")
    parser.add_argument("--file", required=True, help="Path to CSV")
    args = parser.parse_args()
    n = asyncio.run(run(args.file))
    print(f"Imported {n} parts.")


if __name__ == "__main__":
    main()
