"""Every email WearWise sends goes through here (docs/AGENTS.md, section 7; D57), so the
allowlist and the daily cap hold for all of them, and each is recorded in email_events, without
its address.

Until a domain is verified, the provider sends only to its account owner's address, so
EMAIL_ALLOWLIST lists that address and anything else is held, not sent. The daily cap stays
under the provider's daily limit; anything held by it is for the next run to send.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.email import Email, EmailSender, EmailUnavailable
from app.core.config import get_settings
from app.models import EmailEvent

KEPT_FOR = timedelta(days=90)


def sent_today(db: Session, now: datetime) -> int:
    """Emails sent since midnight UTC, when the provider's daily count starts again."""
    midnight = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.scalar(
            select(func.count())
            .select_from(EmailEvent)
            .where(EmailEvent.status == "sent", EmailEvent.created_at >= midnight)
        )
        or 0
    )


def send(
    db: Session,
    sender: EmailSender,
    email: Email,
    kind: str,
    now: datetime,
    user_id: uuid.UUID | None = None,
) -> EmailEvent:
    """Send one email if the allowlist and the daily cap allow it, and record what happened.
    The caller commits."""
    settings = get_settings()
    allowed = settings.email_allowed
    provider_id: str | None = None
    error: str | None = None
    if allowed and email.to.strip().lower() not in allowed:
        status = "held_by_allowlist"
    elif sent_today(db, now) >= settings.email_daily_cap:
        status = "held_by_daily_cap"
    else:
        try:
            provider_id = sender.send(email)
            status = "sent"
        except EmailUnavailable as failure:
            status = "failed"
            error = failure.reason
    event = EmailEvent(
        user_id=user_id, kind=kind, status=status, provider_message_id=provider_id, error=error
    )
    db.add(event)
    db.flush()
    return event
