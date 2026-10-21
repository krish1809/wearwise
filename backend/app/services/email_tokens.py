"""Links sent by email that work once and expire (D57): confirming an address, and setting a new
password. The token is 256 random bits in the link; only its hash is stored, like a session's.
Asking again stops the earlier link working."""

import secrets
from datetime import datetime, timedelta

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from app.core.security import hash_session_token
from app.models import EmailToken, User

LIFETIMES = {
    "confirm_email": timedelta(days=2),
    "password_reset": timedelta(hours=1),
}


def issue(db: Session, user: User, purpose: str, now: datetime) -> str:
    """A new link's token for this person and purpose. The caller commits."""
    db.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user.id,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    token = secrets.token_urlsafe(32)
    db.add(
        EmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_session_token(token),
            expires_at=now + LIFETIMES[purpose],
        )
    )
    db.flush()
    return token


def redeem(db: Session, token: str, purpose: str, now: datetime) -> User | None:
    """The person a valid, unused, unexpired token is for, using it up; None otherwise. The
    caller commits."""
    row = db.scalar(
        select(EmailToken)
        .where(EmailToken.token_hash == hash_session_token(token), EmailToken.purpose == purpose)
        .with_for_update()
    )
    if row is None or row.used_at is not None or row.expires_at <= now:
        return None
    row.used_at = now
    return db.get(User, row.user_id)


def waiting(db: Session, user: User, purpose: str, now: datetime) -> bool:
    """Whether a link for this has been sent and can still be used."""
    return bool(
        db.scalar(
            select(
                exists().where(
                    EmailToken.user_id == user.id,
                    EmailToken.purpose == purpose,
                    EmailToken.used_at.is_(None),
                    EmailToken.expires_at > now,
                )
            )
        )
    )
