import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, SmallInteger, String, false
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Candidate(IdMixin, TimestampMixin, Base):
    """Something the person is thinking of buying: described like an item, so the engine can
    say what it would add (docs/SHOPPING.md)."""

    __tablename__ = "candidates"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # manual (typed in), archetype (a staple from gaps or the capsule), link (read from a
    # pasted page), or catalog (from the demo catalogue).
    source: Mapped[str] = mapped_column(default="manual", server_default="manual")
    archetype_id: Mapped[str | None] = mapped_column(ForeignKey("archetypes.id"))
    # Optional; the app shows "colour + category" when it's empty.
    name: Mapped[str | None]
    brand: Mapped[str | None]
    # Where the person saw it. Read once, when pasted, if the site allows it (M9).
    url: Mapped[str | None]
    # The shop's own picture, shown from the shop's address (never copied here).
    image_url: Mapped[str | None]
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
    # "Wait before buying": the day to ask again whether it's still wanted. Cleared once the
    # person answers, skips it, or buys it.
    remind_on: Mapped[date | None] = mapped_column(Date)
    # The last analysis and verdict, and the key it was made under: everything it depends on
    # (wardrobe version, engine version, occasions, styles, budgets, the candidate itself).
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    analysis_key: Mapped[str | None]
    # The wardrobe item made from it once bought.
    item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"))


Index("ix_candidates_user_id_created_at", Candidate.user_id, Candidate.created_at)
Index("ix_candidates_category_id", Candidate.category_id)
# Deleting an item clears the bought candidate's link to it.
Index("ix_candidates_item_id", Candidate.item_id, postgresql_where=Candidate.item_id.is_not(None))


class LinkPreview(IdMixin, TimestampMixin, Base):
    """What one pasted page said, kept a day so it's read at most once a day. Public page
    data only: nothing about who pasted it."""

    __tablename__ = "link_previews"

    url: Mapped[str] = mapped_column(unique=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # ok, blocked (robots.txt), unavailable, or not_product.
    outcome: Mapped[str]
    # The page's preview data, when it was read.
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")


class CatalogProduct(IdMixin, TimestampMixin, Base):
    """A product from a catalogue: in M9 only the demo catalogue, loaded by a script from an
    open dataset and always marked as demo."""

    __tablename__ = "catalog_products"

    source: Mapped[str]
    external_id: Mapped[str]
    title: Mapped[str]
    brand: Mapped[str | None]
    url: Mapped[str | None]
    image_url: Mapped[str | None]
    # Minor units; demo products have none.
    price: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(default="INR", server_default="INR")
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    color_primary: Mapped[str] = mapped_column(ForeignKey("color_families.id"))
    pattern: Mapped[str] = mapped_column(default="solid", server_default="solid")
    fabric: Mapped[str | None]
    formality: Mapped[int] = mapped_column(SmallInteger)
    warmth: Mapped[int] = mapped_column(SmallInteger)
    seasons: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    sections: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(default=True, server_default=false())


Index(
    "uq_catalog_products_source_external_id",
    CatalogProduct.source,
    CatalogProduct.external_id,
    unique=True,
)
Index("ix_catalog_products_category_id", CatalogProduct.category_id)
