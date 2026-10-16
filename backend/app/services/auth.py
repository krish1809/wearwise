"""Accounts and sessions: create an account, check a password, start, find, and end a login."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    burn_password_check,
    hash_password,
    hash_session_token,
    new_session_token,
    password_needs_rehash,
    verify_password,
)
from app.models.user import User
from app.models.user_session import UserSession

# A session's expiry moves forward when it's used, at most once a day to save writes.
REFRESH_SESSION_AFTER = timedelta(days=1)


class EmailTaken(Exception):
    """An account with this email already exists."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register(db: Session, *, email: str, password: str, name: str | None) -> User:
    """Create an account. The caller has already checked the password against the policy."""
    email = normalize_email(email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EmailTaken
    user = User(email=email, password_hash=hash_password(password), name=name)
    try:
        with db.begin_nested():
            db.add(user)
    except IntegrityError as error:  # the same email registered a moment ago
        raise EmailTaken from error
    return user


def authenticate(db: Session, *, email: str, password: str) -> User | None:
    """The account for this email and password, or None. Takes as long either way."""
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        burn_password_check(password)
        return None
    if not verify_password(user.password_hash, password):
        return None
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


def start_session(
    db: Session,
    user: User,
    *,
    days: int,
    user_agent: str | None,
    now: datetime | None = None,
) -> str:
    """Store a new session and return the token for the cookie."""
    now = now or datetime.now(UTC)
    token = new_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=now + timedelta(days=days),
            last_seen_at=now,
            user_agent=(user_agent or "")[:300] or None,
        )
    )
    db.flush()
    return token


def user_for_session(
    db: Session, token: str, *, days: int, now: datetime | None = None
) -> User | None:
    """The logged-in user for a cookie token, or None if the session is unknown or expired."""
    now = now or datetime.now(UTC)
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == hash_session_token(token))
    ).one_or_none()
    if row is None:
        return None
    session, user = row
    if session.expires_at <= now:
        db.delete(session)
        return None
    if now - session.last_seen_at >= REFRESH_SESSION_AFTER:
        session.last_seen_at = now
        session.expires_at = now + timedelta(days=days)
    return user


def end_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == hash_session_token(token)))
