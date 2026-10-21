import uuid
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class SavedMeasures(IdMixin, TimestampMixin, Base):
    """A person's latest wardrobe measures (Insights), kept so they outlast the server's sleep:
    worked out again only when something they depend on changes (`key`, D53)."""

    __tablename__ = "saved_measures"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    # A hash of everything the measures depend on: the wardrobe version, the engine version,
    # the occasions, styles, colours, and reactions, and the seasons.
    key: Mapped[str]
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
