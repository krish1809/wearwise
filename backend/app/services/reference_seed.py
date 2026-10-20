"""Load the reference lists in seed/ into the database.

Safe to run on every deploy. Rows are inserted or updated by id and never deleted, because
profiles and items refer to them by id; a row dropped from a seed file stays until a migration
retires it. Custom categories (those with a user_id) are never touched. Rows that haven't
changed aren't rewritten, so their updated_at stays put.
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import (
    Category,
    CategoryGroup,
    ColorFamily,
    Occasion,
    OutfitTemplate,
    StyleProfile,
    VocabularyTerm,
)
from app.models.base import Base

SEED_DIR = Path(__file__).resolve().parents[3] / "seed"

# taxonomy.json lists that become vocabulary_terms rows, keyed by kind.
VOCABULARY_KINDS = {
    "section": "sections",
    "fit": "fits",
    "sizing_system": "sizing_systems",
    "slot": "slots",
    "pattern": "patterns",
    "fabric": "fabrics",
    "season": "seasons",
    "status": "statuses",
}


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
            # Some lists are bare ids ("slim"); others carry a display name, and slots a kind.
            term_id = entry if isinstance(entry, str) else entry["id"]
            name = entry["name"] if isinstance(entry, dict) else _title(entry)
            role = entry.get("kind") if isinstance(entry, dict) else None
            vocabulary.append(
                {"kind": kind, "id": term_id, "name": name, "role": role, "position": position}
            )
    # The formality scale is a mapping, "1": "Lounge / sport" to "5": "Formal / ceremonial".
    for position, (level, name) in enumerate(sorted(taxonomy["formality_scale"].items())):
        vocabulary.append(
            {"kind": "formality", "id": level, "name": name, "role": None, "position": position}
        )

    categories = taxonomy["categories"]
    _ids("taxonomy.json categories", categories)
    slot_ids = _ids("taxonomy.json slots", taxonomy["slots"])
    section_ids = set(taxonomy["sections"])
    for category in categories:
        problems = []
        if category["group"] not in group_ids:
            problems.append(f"group {category['group']!r}")
        if category["slot"] not in slot_ids:
            problems.append(f"slot {category['slot']!r}")
        if set(category["sections"]) - section_ids:
            problems.append(f"sections {sorted(set(category['sections']) - section_ids)}")
        if problems:
            raise SeedError(f"Category {category['id']!r} has unknown {', '.join(problems)}")

    templates = taxonomy["outfit_templates"]
    _ids("taxonomy.json outfit_templates", templates)
    category_ids = {c["id"] for c in categories}
    for template in templates:
        named_slots = [r["slot"] for r in template["required"]] + template["optional"]
        named_categories = [
            c
            for r in template["required"]
            for c in r.get("categories", []) + r.get("exclude_categories", [])
        ]
        strangers = sorted(set(named_slots) - slot_ids) + sorted(
            set(named_categories) - category_ids
        )
        if strangers:
            raise SeedError(f"Outfit template {template['id']!r} names unknown {strangers}")

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
        "categories": _upsert(
            db,
            Category,
            [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "group_id": c["group"],
                    "slot": c["slot"],
                    "sections": c["sections"],
                    "formality_default": c["formality_default"],
                    "formality_min": c["formality_min"],
                    "formality_max": c["formality_max"],
                    "warmth": c["warmth"],
                    "wears_before_wash": c["wears_before_wash"],
                    "traits": c.get("traits", []),
                    "position": i,
                }
                for i, c in enumerate(categories)
            ],
        ),
        "outfit_templates": _upsert(
            db,
            OutfitTemplate,
            [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "required": t["required"],
                    "optional": t["optional"],
                    "position": i,
                }
                for i, t in enumerate(templates)
            ],
        ),
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
