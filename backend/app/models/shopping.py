import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Candidate(IdMixin, TimestampMixin, Base):
    """Something the person is thinking of buying: described like an item, so the engine can
    say what it would add (docs/SHOPPING.md)."""

    __tablename__ = "candidates"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # manual (typed in) or archetype (a staple added from gaps or the capsule); M9 adds more.
    source: Mapped[str] = mapped_column(default="manual", server_default="manual")
    archetype_id: Mapped[str | None] = mapped_column(ForeignKey("archetypes.id"))
    # Optional; the app shows "colour + category" when it's empty.
    name: Mapped[str | None]
    brand: Mapped[str | None]
    # Where the person saw it. Stored as given; never fetched in M8.
    url: Mapped[str | None]
    size_label: Mapped[str | None]
    # Minor units (paise). The price is never shown without when it was given.
    price: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(default="INR", server_default="INR")
    price_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_price: Mapped[int | None] = mapped_column(BigInteger)
    # The same attributes as items.
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    slot: Mapped[str]
    color_primary: Mapped[str] = mapped_column(ForeignKey("color_families.id"))
    color_secondary: Mapped[str | None] = mapped_column(ForeignKey("color_families.id"))
    color_hex: Mapped[str | None]
    pattern: Mapped[str] = mapped_column(default="solid", server_default="solid")
    fabric: Mapped[str | None]
    fit: Mapped[str | None]
    formality: Mapped[int] = mapped_column(SmallInteger)
    warmth: Mapped[int] = mapped_column(SmallInteger)
    seasons: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    # considering, buy_next, later, skipped, or purchased.
    status: Mapped[str] = mapped_column(default="considering", server_default="considering")
    notes: Mapped[str | None]
    # The last analysis and verdict, and the key it was made under: everything it depends on
    # (wardrobe version, engine version, occasions, styles, budgets, the candidate itself).
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    analysis_key: Mapped[str | None]
    # The wardrobe item made from it once bought.
    item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"))


Index("ix_candidates_user_id_created_at", Candidate.user_id, Candidate.created_at)
