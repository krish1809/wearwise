"""Reference data: the lists the app offers, loaded from seed/ by the seed script.

Each table uses the seed file's id (a slug such as "navy" or "college") as its primary key, so
other rows can refer to it and the ids stay stable when display names change.
"""

from typing import Any

from sqlalchemy import String
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
    """Short fixed lists from taxonomy.json: sections, fits, sizing systems."""

    __tablename__ = "vocabulary_terms"

    kind: Mapped[str] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    position: Mapped[int]
