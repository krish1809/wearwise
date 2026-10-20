"""Auto-tagging a photo (docs/AI.md, section 2): the image goes to the model with a schema
whose choices are the real ids from the database; anything outside them is dropped. Only
the image is sent: no name, email, or measurements. The person checks every field before
saving, and fabric is only ever a guess to check against the label."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.ai import AIProvider, AIUnavailable
from app.adapters.storage import Storage
from app.models import ColorFamily, User
from app.services import ai_usage, categories, photos, reference

INSTRUCTIONS = (
    "Describe the one garment, pair of shoes, or accessory in this photo for a wardrobe "
    "app. Choose the closest allowed value for each field. Leave out any field you can't "
    "tell from the photo. Give a fabric only when the texture makes it clear; it will be "
    "checked against the label."
)
FIELDS = ("category_id", "color_primary", "color_secondary", "pattern", "fabric", "fit")


class PhotoMissing(Exception):
    pass


@dataclass(frozen=True)
class Suggested:
    fields: dict[str, str]


def schema(db: Session, user: User) -> dict[str, Any]:
    found = categories.list_categories(db, user)
    colours = reference.ordered(db, ColorFamily)

    def choice(values: list[tuple[str, str]], what: str) -> dict[str, Any]:
        return {
            "type": "string",
            "enum": [value for value, _ in values],
            "description": f"{what}. " + "; ".join(f"{value} = {name}" for value, name in values),
        }

    def terms(kind: str) -> list[tuple[str, str]]:
        return [(term.id, term.name) for term in reference.terms(db, kind)]

    colour_values = [(c.id, c.name) for c in colours]
    return {
        "type": "object",
        "properties": {
            "category_id": choice([(c.id, c.name) for c in found], "What kind of item it is"),
            "color_primary": choice(colour_values, "Its main colour"),
            "color_secondary": choice(colour_values, "A second colour, if there's a clear one"),
            "pattern": choice(terms("pattern"), "Its pattern"),
            "fabric": choice(terms("fabric"), "Its fabric, only if clear from the texture"),
            "fit": choice(terms("fit"), "Its fit, only if clear"),
        },
        "required": ["category_id", "color_primary"],
    }


def tag(
    db: Session, user: User, storage: Storage, ai: AIProvider | None, photo_id: Any
) -> Suggested:
    """Suggestions for an uploaded photo. Raises PhotoMissing, AIOff, or AIUnavailable."""
    photo = photos.find_photo(db, user, photo_id)
    if photo is None:
        raise PhotoMissing
    ai_usage.check_image(db, user, ai)
    assert ai is not None
    image = storage.get(photo.thumb_key) or storage.get(photo.storage_key)
    if image is None:
        raise PhotoMissing
    shape = schema(db, user)
    # Nothing is held open while the model looks at the photo.
    db.commit()
    try:
        tagged = ai.tag_image(image, "image/webp", shape, INSTRUCTIONS)
    except AIUnavailable:
        raise
    ai_usage.record(db, user, tagged.usage, images=1)
    allowed = {name: set(prop["enum"]) for name, prop in shape["properties"].items()}
    fields = {
        name: value
        for name, value in tagged.fields.items()
        if name in FIELDS and isinstance(value, str) and value in allowed[name]
    }
    if fields.get("color_secondary") == fields.get("color_primary"):
        fields.pop("color_secondary", None)
    return Suggested(fields)
