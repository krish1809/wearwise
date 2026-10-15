"""Reference data: the lists the app offers, loaded from seed/ by the seed script.

Each table uses the seed file's id (a slug such as "navy" or "college") as its primary key, so
other rows can refer to it and the ids stay stable when display names change.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ColorFamily(TimestampMixin, Base):
    __tablename__ = "color_families"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    # A representative swatch colour; empty for "multicolour", which has no single one.
    hex: Mapped[str | None]
    # 1 pairs with anything, 0 is a full colour.
    neutrality: Mapped[float]
    position: Mapped[int]


class Occasion(TimestampMixin, Base):
    __tablename__ = "occasions"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    formality_min: Mapped[int]
    formality_max: Mapped[int]
    prefers_groups: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")
    hint: Mapped[str | None]
    position: Mapped[int]


class StyleProfile(TimestampMixin, Base):
    __tablename__ = "style_profiles"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]
    # The colours, fabrics, fits, and categories that signal the style (used by the engine in M5).
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB)
    position: Mapped[int]


class CategoryGroup(TimestampMixin, Base):
    """Broad groups such as tops or footwear, used for typical spend in the budget."""

    __tablename__ = "category_groups"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    position: Mapped[int]


class VocabularyTerm(TimestampMixin, Base):
    """Short fixed lists from taxonomy.json: sections, fits, sizing systems, slots, and more."""

    __tablename__ = "vocabulary_terms"

    kind: Mapped[str] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    # Slots only: "core" (top, bottom, footwear...), "accessory", or "finishing" (fragrance).
    role: Mapped[str | None]
    position: Mapped[int]


class Category(TimestampMixin, Base):
    """A kind of garment or accessory. Seeded rows have no user_id; custom ones have an owner."""

    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(primary_key=True)
    # Null for the seeded categories everyone sees.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str]
    group_id: Mapped[str] = mapped_column(ForeignKey("category_groups.id"))
    # Which outfit slot it fills (top, footwear, watch...): a vocabulary_terms id of kind "slot".
    slot: Mapped[str]
    # Which sections show it by default; every category stays available through "show all".
    sections: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")
    # Defaults for new items, on the 1 (lounge) to 5 (formal) scale. Items can override them.
    formality_default: Mapped[int]
    formality_min: Mapped[int]
    formality_max: Mapped[int]
    # 0 none to 5 heavy.
    warmth: Mapped[int]
    # Null when it isn't washed on a schedule (shoes, watches, a leather jacket).
    wears_before_wash: Mapped[int | None]
    position: Mapped[int]


# A person can't have two custom categories with the same name, whatever the capitalisation.
Index(
    "uq_categories_user_id_name",
    Category.user_id,
    func.lower(Category.name),
    unique=True,
    postgresql_where=Category.user_id.is_not(None),
)


class OutfitTemplate(TimestampMixin, Base):
    """A shape an outfit can take, such as top, bottom, and footwear. From taxonomy.json."""

    __tablename__ = "outfit_templates"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    # Each requirement: {"slot": ..., and optionally "categories": [...] (only these) or
    # "exclude_categories": [...] (not these)}.
    required: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    # Slots that may be added: layers, accessories, fragrance.
    optional: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")
    position: Mapped[int]
