import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class EmailEvent(IdMixin, TimestampMixin, Base):
    """One email WearWise sent, or held back, and why (docs/AGENTS.md, section 7). Never the
    address: who it was for is the account, or nobody for the owner's run reports. Kept 90
    days."""

    __tablename__ = "email_events"

    # The person it was for; None for the owner's run reports, which go to ADMIN_EMAILS.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # digest, confirm, password_reset, or run_report.
    kind: Mapped[str]
    # sent, failed, held_by_allowlist, or held_by_daily_cap.
    status: Mapped[str]
    provider_message_id: Mapped[str | None]
    error: Mapped[str | None]


Index(
    "ix_email_events_user_id",
    EmailEvent.user_id,
    postgresql_where=EmailEvent.user_id.is_not(None),
)
# The daily cap counts today's sends; housekeeping removes old rows.
Index("ix_email_events_created_at", EmailEvent.created_at)


class EmailToken(IdMixin, TimestampMixin, Base):
    """A link sent by email that works once and expires: confirming an address, or setting a
    new password. Only its hash is stored, like a session's."""

    __tablename__ = "email_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # confirm_email or password_reset.
    purpose: Mapped[str]
    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("ix_email_tokens_user_id", EmailToken.user_id)
