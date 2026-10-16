import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Outfit(IdMixin, TimestampMixin, Base):
    """A saved combination of the person's items, one per slot."""

    __tablename__ = "outfits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Optional; the app names it after its main pieces when empty.
    name: Mapped[str | None]
    # The template it fills, worked out from its pieces when it's saved.
    template_id: Mapped[str | None] = mapped_column(ForeignKey("outfit_templates.id"))
    occasion_id: Mapped[str | None] = mapped_column(ForeignKey("occasions.id"))
    is_favorite: Mapped[bool] = mapped_column(default=False, server_default=false())


class OutfitItem(IdMixin, TimestampMixin, Base):
    """One piece of an outfit. If the item is deleted, the row stays with its name, so the
    outfit shows the piece as removed instead of breaking."""

    __tablename__ = "outfit_items"

    outfit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("outfits.id", ondelete="CASCADE"))
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"), index=True
    )
    slot: Mapped[str]
    # The item's name when it was added, shown once the item is deleted.
    item_name: Mapped[str]


# One item per slot; this also serves lookups by outfit.
Index("uq_outfit_items_outfit_id_slot", OutfitItem.outfit_id, OutfitItem.slot, unique=True)


class WearLog(IdMixin, TimestampMixin, Base):
    """One time the person wore something: a saved outfit or loose items, on a day."""

    __tablename__ = "wear_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    worn_on: Mapped[date] = mapped_column(Date)
    # The outfit it came from, if any. Deleting the outfit keeps the log.
    outfit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("outfits.id", ondelete="SET NULL"), index=True
    )
    occasion_id: Mapped[str | None] = mapped_column(ForeignKey("occasions.id"))
    note: Mapped[str | None]


Index("ix_wear_logs_user_id_worn_on", WearLog.user_id, WearLog.worn_on)


class WearLogItem(IdMixin, TimestampMixin, Base):
    """An item worn in a wear log: the record every wear count is built from. An outfit is
    copied into these rows when it's logged, so editing the outfit later doesn't change history."""

    __tablename__ = "wear_log_items"

    wear_log_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wear_logs.id", ondelete="CASCADE"))
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"), index=True
    )
    # The item's slot and name when it was logged, shown once the item is deleted.
    slot: Mapped[str]
    item_name: Mapped[str]


Index(
    "uq_wear_log_items_wear_log_id_item_id",
    WearLogItem.wear_log_id,
    WearLogItem.item_id,
    unique=True,
)
