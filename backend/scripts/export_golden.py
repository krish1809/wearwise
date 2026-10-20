"""Export one account's wardrobe so its owner can label the golden set (docs/ENGINE.md, 9).

Writes backend/tests/golden/items.json, pairs.csv (with an empty label column), and
outfits.json (the account's favourite outfits that have an occasion). Open pairs.csv in a
spreadsheet and put good, fine, or bad in each label cell; then `make test` checks the
engine against your labels.

Usage, against the database in .env or another one:
  uv run python -m scripts.export_golden --email you@example.com
  DATABASE_URL='postgresql://...' uv run python -m scripts.export_golden --email you@example.com

The files hold item names and attributes, never photos. pairs.csv is not overwritten once it
has labels, unless you pass --force.
"""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from sqlalchemy import func, select

from app.core.db import get_sessionmaker
from app.engine.golden import candidate_pairs, item_to_dict, read_labels, write_pairs
from app.models import Outfit, User
from app.services import outfits as outfit_service
from app.services import suggestions, wear

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "tests" / "golden"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a wardrobe for golden-set labelling.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--pairs", type=int, default=80, help="how many pairs to label (60+)")
    parser.add_argument("--out", type=Path, default=GOLDEN_DIR)
    parser.add_argument("--force", action="store_true", help="replace a labelled pairs.csv")
    args = parser.parse_args()

    pairs_file = args.out / "pairs.csv"
    if pairs_file.exists() and read_labels(pairs_file.read_text()) and not args.force:
        sys.exit(f"{pairs_file} already has labels. Pass --force to replace it.")

    with get_sessionmaker()() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == args.email.lower()))
        if user is None:
            sys.exit(f"No account with the email {args.email}.")
        wardrobe = suggestions.load_wardrobe(db, user, wear.today())
        keys = {item.id: f"i{index:02d}" for index, item in enumerate(wardrobe.items, start=1)}
        items = [item_to_dict(item, keys[item.id]) for item in wardrobe.items]
        favourites = list(
            db.scalars(
                select(Outfit).where(
                    Outfit.user_id == user.id, Outfit.is_favorite, Outfit.occasion_id.is_not(None)
                )
            )
        )
        pieces = outfit_service.pieces_of(db, [outfit.id for outfit in favourites])
        core = {slot for slot, kind in wardrobe.slot_kinds.items() if kind == "core"}
        loved = []
        for outfit in favourites:
            ids = [str(p.item_id) for p in pieces[outfit.id] if p.item_id and p.slot in core]
            if ids and all(item_id in keys for item_id in ids):
                loved.append(
                    {
                        "occasion": outfit.occasion_id,
                        "items": sorted(keys[item_id] for item_id in ids),
                        "name": outfit.name or "",
                    }
                )

    renamed = [replace(item, id=keys[item.id]) for item in wardrobe.items]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "items.json").write_text(json.dumps(items, indent=1) + "\n")
    pairs_file.write_text(write_pairs(candidate_pairs(renamed, args.pairs)))
    (args.out / "outfits.json").write_text(json.dumps(loved, indent=1) + "\n")
    print(f"Exported {len(items)} items, {len(loved)} favourite outfits, to {args.out}.")
    print(f"Next: put good, fine, or bad in each label cell of {pairs_file}.")


if __name__ == "__main__":
    main()
