#!/usr/bin/env python3
"""
CLI to import source CSV files into the source registry.

Usage:
    python import_sources.py --file data/sources_buyable.csv --type buyable
    python import_sources.py --file data/sources_reference.csv --type reference
    python import_sources.py --all   # imports both default files
"""

import argparse
import csv
import sys
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.data.source_registry import get_registry_stats, normalize_domain, parse_tags, upsert_source

# Priority defaults by category (higher = searched first)
CATEGORY_PRIORITIES = {
    "retailer": 60,
    "marketplace": 50,
    "used_aggregator": 55,
    "salvage_yard": 45,
    "oe_dealer": 70,
    "industrial": 30,
    "electronics": 25,
    "interchange": 65,
    "epc": 40,
    "epc_retail": 45,
    "oem_catalog": 75,
}


def import_csv(filepath: str, source_type: str) -> int:
    """Import sources from a CSV file. Returns count of sources upserted."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = normalize_domain(row["domain"])
            name = row["name"].strip()
            category = row["category"].strip().lower()
            tags = parse_tags(row.get("tags", ""))
            notes = row.get("notes", "").strip()
            priority = CATEGORY_PRIORITIES.get(category, 50)

            upsert_source(
                domain=domain,
                name=name,
                category=category,
                tags=tags,
                notes=notes,
                source_type=source_type,
                priority=priority,
            )
            count += 1
            print(f"  {'✓':>2} {domain:<40} {category:<20} [{', '.join(tags[:3])}]")

    return count


def main():
    parser = argparse.ArgumentParser(description="Import source CSVs into the registry")
    parser.add_argument("--file", type=str, help="Path to CSV file")
    parser.add_argument("--type", type=str, choices=["buyable", "reference"], help="Source type")
    parser.add_argument("--all", action="store_true", help="Import both default CSV files")
    args = parser.parse_args()

    if args.all:
        base = Path(__file__).parent / "data"
        print("Importing buyable sources...")
        n1 = import_csv(str(base / "sources_buyable.csv"), "buyable")
        print("\nImporting reference sources...")
        n2 = import_csv(str(base / "sources_reference.csv"), "reference")
        print(f"\nDone: {n1} buyable + {n2} reference = {n1 + n2} total sources")
    elif args.file and args.type:
        print(f"Importing {args.type} sources from {args.file}...")
        n = import_csv(args.file, args.type)
        print(f"\nDone: {n} sources imported")
    else:
        parser.print_help()
        sys.exit(1)

    stats = get_registry_stats()
    print(f"\nRegistry: {stats['total']} total, {stats['active']} active")
    print(f"By type: {stats['by_source_type']}")
    print(f"By category: {stats['by_category']}")


if __name__ == "__main__":
    main()
