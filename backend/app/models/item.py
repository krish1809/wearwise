import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, SmallInteger, String, true
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Item(IdMixin, TimestampMixin, Base):
    """One thing the person owns: a garment, shoes, an accessory, a fragrance."""

    __tablename__ = "items"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # A custom category can't be deleted while items use it (checked in the service; the
    # database checks at the end of each statement, so deleting an account removes both).
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    # Copied from the category, so filtering by slot needs no join.
    slot: Mapped[str]
    # Optional; the app shows "colour + category" when it's empty.
    name: Mapped[str | None]
    brand: Mapped[str | None]
    size_label: Mapped[str | None]
    color_primary: Mapped[str] = mapped_column(ForeignKey("color_families.id"))
    color_secondary: Mapped[str | None] = mapped_column(ForeignKey("color_families.id"))
    # Measured from the photo, or picked; more exact than the family.
    color_hex: Mapped[str | None]
    pattern: Mapped[str] = mapped_column(default="solid", server_default="solid")
    fabric: Mapped[str | None]
    fit: Mapped[str | None]
    # 1 (lounge) to 5 (formal), and warmth 0 to 5. Both start from the category's defaults.
    formality: Mapped[int] = mapped_column(SmallInteger)
    warmth: Mapped[int] = mapped_column(SmallInteger)
    # Empty means every season.
    seasons: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    occasion_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    # Style profile ids and the person's own tags.
    style_tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    # Minor units (paise for INR).
    price: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(default="INR", server_default="INR")
    purchased_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(default="available", server_default="available")
    # Null for things that aren't washed on a schedule.
    wears_before_wash: Mapped[int | None] = mapped_column(SmallInteger)
    # Wears logged after the last wash; recounted from the wear log whenever it changes.
    wears_since_wash: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    # When it last came back from the laundry. Wears on or before this day don't count.
    last_washed_on: Mapped[date | None] = mapped_column(Date)
    # Items sharing a set id are a matching set, such as a suit's jacket and trousers.
    set_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    # Extras for one slot, such as a fragrance's scent family.
    attrs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    notes: Mapped[str | None]
    # Archived items are hidden from the wardrobe and suggestions but kept.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("ix_items_user_id_archived_at", Item.user_id, Item.archived_at)
Index("ix_items_user_id_created_at", Item.user_id, Item.created_at)
Index("ix_items_user_id_slot", Item.user_id, Item.slot)
Index("ix_items_user_id_category_id", Item.user_id, Item.category_id)
Index("ix_items_seasons", Item.seasons, postgresql_using="gin")
Index("ix_items_occasion_ids", Item.occasion_ids, postgresql_using="gin")
Index("ix_items_style_tags", Item.style_tags, postgresql_using="gin")


class ItemImage(IdMixin, TimestampMixin, Base):
    """A stored photo. It belongs to its uploader, and to an item once one is saved with it."""

    __tablename__ = "item_images"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Null between the upload and saving the item; unattached photos are cleaned up later.
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), index=True
    )
    # Keys in the storage backend: the photo (at most 1600 px) and a 400 px thumbnail.
    storage_key: Mapped[str]
    thumb_key: Mapped[str]
    width: Mapped[int]
    height: Mapped[int]
    is_primary: Mapped[bool] = mapped_column(default=True, server_default=true())
    dominant_hex: Mapped[str | None]
