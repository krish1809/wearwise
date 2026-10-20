import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, Uuid, false
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Suggestion(IdMixin, TimestampMixin, Base):
    """An outfit the engine showed, kept so feedback, saving, and wearing refer to exactly
    what was shown, and so acceptance can be measured per engine version."""

    __tablename__ = "suggestions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # occasion (no anchors), with_item (one), or complete (two or more).
    kind: Mapped[str]
    occasion_id: Mapped[str | None] = mapped_column(ForeignKey("occasions.id"))
    season: Mapped[str | None]
    template_id: Mapped[str] = mapped_column(ForeignKey("outfit_templates.id"))
    # Every piece in slot order, and the core pieces (required slots and the layer), sorted.
    # Plain arrays, not foreign keys: a deleted item makes the suggestion stale, not broken.
    item_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid))
    core_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid))
    score: Mapped[float]
    components: Mapped[dict[str, float]] = mapped_column(JSONB)
    # [{code, kind, text}], strongest first.
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    compromise: Mapped[bool] = mapped_column(default=False, server_default=false())
    engine_version: Mapped[str]
    # What became of it: the current rating, the outfit it was saved as, the log it was worn in.
    rating: Mapped[str | None]
    saved_outfit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("outfits.id", ondelete="SET NULL")
    )
    wear_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("wear_logs.id", ondelete="SET NULL")
    )
    worn_on: Mapped[date | None] = mapped_column(Date)


Index("ix_suggestions_user_id_created_at", Suggestion.user_id, Suggestion.created_at)


class SuggestionFeedback(IdMixin, TimestampMixin, Base):
    """One reaction to a suggestion: like, dislike, skip, saved, or worn. Pair preferences
    and the like-rates behind the preference score are worked out from these rows each time
    the engine runs, so they can never disagree with them."""

    __tablename__ = "suggestion_feedback"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suggestions.id", ondelete="SET NULL"), index=True
    )
    # The core pieces, sorted.
    item_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid))
    occasion_id: Mapped[str | None] = mapped_column(ForeignKey("occasions.id"))
    verdict: Mapped[str]
    # Why a dislike: the item, the colours, the formality, the occasion, or something else.
    reason: Mapped[str | None]
    # The one item a dislike is about, when the reason is the item.
    item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"))
    engine_version: Mapped[str]
