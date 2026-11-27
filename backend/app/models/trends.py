import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


def _ids() -> Mapped[list[str]]:
    return mapped_column(ARRAY(String), default=list, server_default="{}")


class Trend(IdMixin, TimestampMixin, Base):
    """Something in fashion now, found by the Trend Scout with its sources (docs/AGENTS.md,
    section 4). Shared: nothing about any person."""

    __tablename__ = "trends"

    name: Mapped[str]
    # The name normalised, for recognising the same trend found again.
    name_key: Mapped[str] = mapped_column(index=True)
    # At most 40 words.
    summary: Mapped[str]
    why_now: Mapped[str]
    # All from the seed lists: categories, colour families, fabrics, patterns, fits, seasons,
    # sections, and style profiles.
    category_ids: Mapped[list[str]] = _ids()
    color_families: Mapped[list[str]] = _ids()
    fabrics: Mapped[list[str]] = _ids()
    patterns: Mapped[list[str]] = _ids()
    fits: Mapped[list[str]] = _ids()
    seasons: Mapped[list[str]] = _ids()
    sections: Mapped[list[str]] = _ids()
    style_profile_ids: Mapped[list[str]] = _ids()
    # pending (waiting for the owner), approved, rejected, or expired (not seen for 8 weeks).
    status: Mapped[str]
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The run that found it.
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL")
    )


Index("ix_trends_status_last_seen_at", Trend.status, Trend.last_seen_at)


class TrendSource(IdMixin, TimestampMixin, Base):
    """A page a trend was found in, with the words in it that support the trend."""

    __tablename__ = "trend_sources"

    # Indexed by the unique index below, which starts with it.
    trend_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trends.id", ondelete="CASCADE"))
    url: Mapped[str]
    # The site, without www., so two sources from one site count once.
    domain: Mapped[str]
    title: Mapped[str]
    published_on: Mapped[date] = mapped_column(Date)
    # Found word for word in the text that was read.
    quote: Mapped[str]
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL")
    )


Index("uq_trend_sources_trend_id_url", TrendSource.trend_id, TrendSource.url, unique=True)
