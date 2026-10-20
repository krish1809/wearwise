"""Engine test helpers: items, occasions, and styles built from the real seed files.

Items here are made up for tests; they never reach a database or an account.
"""

import json
from datetime import date
from itertools import count
from typing import Any

from app.engine.outfits import Template
from app.engine.types import Context, EngineItem, Occasion, Preferences, Style, Wardrobe
from app.services.reference_seed import SEED_DIR

TODAY = date(2026, 10, 16)
USER = "user-a"

_taxonomy = json.loads((SEED_DIR / "taxonomy.json").read_text())
_colors = json.loads((SEED_DIR / "colors.json").read_text())["families"]
_occasions = json.loads((SEED_DIR / "occasions.json").read_text())["occasions"]
_styles = json.loads((SEED_DIR / "style_profiles.json").read_text())["profiles"]

CATEGORIES: dict[str, dict[str, Any]] = {c["id"]: c for c in _taxonomy["categories"]}
COLORS: dict[str, dict[str, Any]] = {c["id"]: c for c in _colors}
TEMPLATES = tuple(
    Template.from_seed(t["id"], t["required"], t["optional"]) for t in _taxonomy["outfit_templates"]
)
SLOT_KINDS = {slot["id"]: slot["kind"] for slot in _taxonomy["slots"]}
SLOT_NAMES = {slot["id"]: slot["name"] for slot in _taxonomy["slots"]}
GROUP_NAMES = {group["id"]: group["name"] for group in _taxonomy["groups"]}
COLOR_NAMES = {c["id"]: c["name"] for c in _colors}
OCCASIONS = {
    o["id"]: Occasion(
        id=o["id"],
        name=o["name"],
        formality_min=o["formality_min"],
        formality_max=o["formality_max"],
        prefers_groups=frozenset(o["prefers_groups"]),
    )
    for o in _occasions
}
STYLES = {
    s["id"]: Style(
        id=s["id"],
        name=s["name"],
        colors=frozenset(s["signals"]["colors"]),
        fabrics=frozenset(s["signals"]["fabrics"]),
        patterns=frozenset(s["signals"]["patterns"]),
        fits=frozenset(s["signals"]["fits"]),
        categories=frozenset(s["signals"]["categories"]),
        formality_center=s["signals"]["formality_center"],
    )
    for s in _styles
}

_ids = count(1)


def make(category: str, color: str = "navy", **fields: Any) -> EngineItem:
    """An item of a seeded category and colour family, with the category's defaults."""
    spec = CATEGORIES[category]
    family = COLORS[color]
    values: dict[str, Any] = {
        "id": f"item-{next(_ids):04d}",
        "owner_id": USER,
        "name": f"{family['name']} {spec['name'].lower()}",
        "slot": spec["slot"],
        "category_id": category,
        "group_id": spec["group"],
        "color_family": color,
        "color_neutrality": family["neutrality"],
        "color_hex": family["hex"],
        "formality": spec["formality_default"],
        "warmth": spec["warmth"],
        "wears_before_wash": spec["wears_before_wash"],
    }
    values.update(fields)
    return EngineItem(**values)


def wardrobe(*items: EngineItem) -> Wardrobe:
    return Wardrobe(
        items=tuple(items),
        templates=TEMPLATES,
        slot_kinds=SLOT_KINDS,
        group_names=GROUP_NAMES,
        slot_names=SLOT_NAMES,
        color_names=COLOR_NAMES,
    )


def context(occasion: str | None = "college", **fields: Any) -> Context:
    values: dict[str, Any] = {
        "user_id": USER,
        "today": TODAY,
        "occasion": OCCASIONS[occasion] if occasion else None,
        "season": "mild",
        "preferences": Preferences(),
    }
    values.update(fields)
    return Context(**values)
