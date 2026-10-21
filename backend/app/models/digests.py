import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Digest(IdMixin, TimestampMixin, Base):
    """One person's picks for one week (docs/AGENTS.md, section 5): built for the weekly email,
    or by "Show this week's picks". At most one per person per ISO week."""

    __tablename__ = "digests"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # The ISO week, such as 2026-W44.
    week: Mapped[str]
    # built (has picks), nothing (nothing worth it), sent, held (not sent: the allowlist or
    # the daily cap), or failed.
    status: Mapped[str]
    # Why there are no picks: no_occasions, no_trends, or nothing_worth_it.
    note: Mapped[str | None]
    season: Mapped[str]
    subject: Mapped[str]
    intro: Mapped[str]
    # template, or model once the weekly email words it.
    wording: Mapped[str] = mapped_column(default="template", server_default="template")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_message_id: Mapped[str | None]
    error: Mapped[str | None]
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


Index("uq_digests_user_id_week", Digest.user_id, Digest.week, unique=True)


class DigestPick(IdMixin, TimestampMixin, Base):
    """One pick in a digest: a piece worth buying, or one the person already owns, for a trend
    in fashion now. Kept as shown, so it still reads the same if the trend is later removed."""

    __tablename__ = "digest_picks"

    # Indexed by the unique index below, which starts with it.
    digest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("digests.id", ondelete="CASCADE"))
    position: Mapped[int]
    # buy, or owned for "already in your wardrobe".
    kind: Mapped[str]
    trend_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trends.id", ondelete="SET NULL"), index=True
    )
    trend_name: Mapped[str]
    trend_summary: Mapped[str]
    # The piece: what to look for, or the person's own.
    name: Mapped[str]
    category_id: Mapped[str]
    color_primary: Mapped[str]
    # A piece to buy: its fabric, pattern, fit, and seasons, as the trend gave them.
    attrs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    score: Mapped[float] = mapped_column(Float)
    # value, trend_fit, and season_fit.
    components: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    # The purchase analysis, for a piece to buy: verdict, new_outfits, coverage_gain,
    # redundancy, and its reasons as sentences.
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # The person's own pieces it names: the owned piece and an outfit with it, or the pieces a
    # new one would be worn with. Plain ids: a deleted item makes the pick stale, not broken.
    item_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(Uuid), default=list, server_default="{}"
    )
    # Where to look: the shop searches, as the product adapter made them.
    query: Mapped[str | None]
    links: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    # The person's usual spend for its kind of clothing, in paise, shown beside the links.
    usual_spend: Mapped[int | None]
    # The sentence shown and sent for it, after the trend's name and summary.
    text: Mapped[str]
    # not_for_me, when the person said so; it lowers similar picks in later weeks.
    verdict: Mapped[str | None]
    verdict_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("uq_digest_picks_digest_id_position", DigestPick.digest_id, DigestPick.position, unique=True)
