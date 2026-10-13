"""Load the reference lists in seed/ into the database.

Safe to run on every deploy. Rows are inserted or updated by id and never deleted, because
profiles (and, from M3, items) refer to them by id; a row dropped from a seed file stays until a
migration retires it. Rows that haven't changed aren't touched, so their updated_at stays put.
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import CategoryGroup, ColorFamily, Occasion, StyleProfile, VocabularyTerm
from app.models.base import Base

SEED_DIR = Path(__file__).resolve().parents[3] / "seed"

# taxonomy.json lists that become vocabulary_terms rows, keyed by kind.
VOCABULARY_KINDS = {"section": "sections", "fit": "fits", "sizing_system": "sizing_systems"}


class SeedError(Exception):
    """A seed file is missing, malformed, or refers to an id that doesn't exist."""


def seed_reference_data(db: Session, seed_dir: Path = SEED_DIR) -> dict[str, int]:
    """Insert or update every reference row. Returns how many rows changed in each table."""
    taxonomy = _load(seed_dir, "taxonomy.json")
    colors = _load(seed_dir, "colors.json")["families"]
    occasions = _load(seed_dir, "occasions.json")["occasions"]
    styles = _load(seed_dir, "style_profiles.json")["profiles"]

    groups = taxonomy["groups"]
    group_ids = _ids("taxonomy.json groups", groups)
    _ids("colors.json", colors)
    _ids("occasions.json", occasions)
    _ids("style_profiles.json", styles)
    for occasion in occasions:
        unknown = set(occasion["prefers_groups"]) - group_ids
        if unknown:
            raise SeedError(f"Occasion {occasion['id']!r} prefers unknown groups {sorted(unknown)}")

    vocabulary: list[dict[str, Any]] = []
    for kind, key in VOCABULARY_KINDS.items():
        entries = taxonomy[key]
        for position, entry in enumerate(entries):
            # Most of these lists are bare ids ("slim"); sizing systems also carry a display name.
            term_id = entry if isinstance(entry, str) else entry["id"]
            name = entry["name"] if isinstance(entry, dict) else _title(entry)
            vocabulary.append({"kind": kind, "id": term_id, "name": name, "position": position})

    changed = {
        "category_groups": _upsert(
            db,
            CategoryGroup,
            [{"id": g["id"], "name": g["name"], "position": i} for i, g in enumerate(groups)],
        ),
        "color_families": _upsert(
            db,
            ColorFamily,
            [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "hex": c["hex"],
                    "neutrality": c["neutrality"],
                    "position": i,
                }
                for i, c in enumerate(colors)
            ],
        ),
        "occasions": _upsert(
            db,
            Occasion,
            [
                {
                    "id": o["id"],
                    "name": o["name"],
                    "formality_min": o["formality_min"],
                    "formality_max": o["formality_max"],
                    "prefers_groups": o["prefers_groups"],
                    "hint": o.get("hint"),
                    "position": i,
                }
                for i, o in enumerate(occasions)
            ],
        ),
        "style_profiles": _upsert(
            db,
            StyleProfile,
            [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "description": s["description"],
                    "signals": s["signals"],
                    "position": i,
                }
                for i, s in enumerate(styles)
            ],
        ),
        "vocabulary_terms": _upsert(db, VocabularyTerm, vocabulary, key=("kind", "id")),
    }
    db.commit()
    return changed


def _load(seed_dir: Path, name: str) -> dict[str, Any]:
    path = seed_dir / name
    try:
        data: dict[str, Any] = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise SeedError(f"Can't read {path}: {error}") from error
    return data


def _ids(label: str, rows: list[dict[str, Any]]) -> set[str]:
    ids = [row["id"] for row in rows]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise SeedError(f"{label} repeats ids {duplicates}")
    return set(ids)


def _title(term_id: str) -> str:
    return term_id.replace("_", " ").capitalize()


def _upsert(
    db: Session,
    model: type[Base],
    rows: Sequence[dict[str, Any]],
    key: tuple[str, ...] = ("id",),
) -> int:
    if not rows:
        return 0
    table = model.__table__
    values = insert(model).values(list(rows))
    columns = [name for name in rows[0] if name not in key]
    statement = values.on_conflict_do_update(
        index_elements=list(key),
        set_={**{name: values.excluded[name] for name in columns}, "updated_at": func.now()},
        # Only rewrite rows whose seed values changed.
        where=or_(*(table.c[name].is_distinct_from(values.excluded[name]) for name in columns)),
    ).returning(table.c[key[0]])
    # RETURNING lists only the rows inserted or rewritten, not the unchanged ones.
    return len(db.execute(statement).all())
