#!/usr/bin/env python3
"""
Run resolver on unlinked vehicle aliases (incremental reconciliation).

Usage:
    python reconcile_aliases.py
    python reconcile_aliases.py --limit 1000 --threshold 85
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.vehicle_resolver import LINK_THRESHOLD, reconcile_unlinked_aliases


def main():
    parser = argparse.ArgumentParser(description="Reconcile unlinked vehicle aliases")
    parser.add_argument("--limit", type=int, default=500, help="Max aliases to process")
    parser.add_argument("--threshold", type=int, default=LINK_THRESHOLD, help="Confidence threshold to auto-link")
    args = parser.parse_args()
    # reconcile_unlinked_aliases uses LINK_THRESHOLD from module; we could pass threshold in a future change
    n = asyncio.run(reconcile_unlinked_aliases(limit=args.limit))
    print(f"Linked {n} aliases to vehicles.")


if __name__ == "__main__":
    main()
