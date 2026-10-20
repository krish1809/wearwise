"""Load a demo catalogue from an open dataset's product list, or remove one.

Written for styles.csv from the "Fashion Product Images" dataset. Check the dataset's licence
before loading it. Every product is marked as demo data, with no price and no link to buy;
WearWise shows it only to rank what kind of piece would add most, never as for sale.

Usage:
  uv run python -m scripts.load_catalog --file path/to/styles.csv
  uv run python -m scripts.load_catalog --clear
"""

import argparse
import csv
import sys
from pathlib import Path

from app.core.db import get_sessionmaker
from app.services.catalog import clear_catalog, load_catalog

SOURCE = "fashion-product-images"


def main() -> None:
    parser = argparse.ArgumentParser(description="Load or remove the demo catalogue.")
    parser.add_argument("--file", type=Path, help="the dataset's styles.csv")
    parser.add_argument("--clear", action="store_true", help="remove the demo catalogue")
    args = parser.parse_args()

    with get_sessionmaker()() as db:
        if args.clear:
            removed = clear_catalog(db, SOURCE)
            db.commit()
            print(f"Demo catalogue removed: {removed} products.")
            return
        if args.file is None or not args.file.is_file():
            sys.exit("Give the dataset's styles.csv with --file.")
        with args.file.open(newline="", encoding="utf-8", errors="replace") as handle:
            loaded = load_catalog(db, csv.DictReader(handle), SOURCE)
        db.commit()
    skipped = ", ".join(f"{reason} {count}" for reason, count in sorted(loaded.skipped.items()))
    print(f"Demo catalogue loaded: {loaded.loaded} products. Skipped: {skipped or 'none'}.")


if __name__ == "__main__":
    main()
