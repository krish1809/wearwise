"""Turning the weekly email on and off (docs/AGENTS.md, section 7; D57).

Off until the person turns it on. The first time, a link goes to their address; following it
confirms the address is theirs and turns the email on, so nobody gets mail they didn't ask for
at an address that isn't theirs. Demo accounts never get email. Unsubscribing from an email, or
turning it off here, stops it until it's turned on again.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.email import Email, EmailSender
from app.core.config import get_settings
from app.models import Profile, User
from app.services import email_links, email_tokens, mail
from app.services import profile as profiles
from app.services.email_layout import Letter


class DemoAccount(Exception):
    """Demo accounts have addresses nobody reads, so they never get email."""


class PreviewOnly(Exception):
    """Until WearWise's email domain is verified, only listed addresses get email, and this
    one isn't listed: a confirmation link would never arrive."""


@dataclass(frozen=True)
class State:
    on: bool
    # A confirmation link has been sent and can still be used.
    waiting_for_confirmation: bool
    # 0 (Monday) to 6 (Sunday).
    weekday: int
    email: str
    confirmed: bool
    # Email can't reach this address yet: it isn't set up in production, or only listed
    # addresses get it until WearWise's domain is verified and this one isn't listed. The
    # picks show on the page, but no email arrives.
    preview_only: bool


def state(db: Session, user: User, now: datetime) -> State:
    profile = profiles.get_or_create_profile(db, user)
    settings = get_settings()
    allowed = settings.email_allowed
    not_set_up = settings.is_production and settings.email_provider == "console"
    return State(
        on=is_on(user, profile),
        waiting_for_confirmation=email_tokens.waiting(db, user, "confirm_email", now),
        weekday=profile.digest_weekday,
        email=user.email,
        confirmed=user.email_verified_at is not None,
        preview_only=not_set_up or (bool(allowed) and user.email not in allowed),
    )


def is_on(user: User, profile: Profile) -> bool:
    return (
        not user.is_demo
        and user.email_verified_at is not None
        and profile.digest_opted_in_at is not None
    )


def turn_on(
    db: Session, user: User, sender: EmailSender, now: datetime, weekday: int | None = None
) -> State:
    """On at once for a confirmed address; otherwise a confirmation link is sent first. The
    caller commits."""
    if user.is_demo:
        raise DemoAccount
    if state(db, user, now).preview_only:
        raise PreviewOnly
    profile = profiles.get_or_create_profile(db, user)
    if weekday is not None:
        profile.digest_weekday = weekday
    if user.email_verified_at is not None:
        profile.digest_opted_in_at = now
        profile.digest_unsubscribed_at = None
    else:
        token = email_tokens.issue(db, user, "confirm_email", now)
        mail.send(db, sender, confirmation(user, token), "confirm", now, user.id)
    return state(db, user, now)


def confirm(db: Session, token: str, now: datetime) -> User | None:
    """Follow a confirmation link: the address is confirmed and the email turned on. None for a
    link that's expired, used, or made up. The caller commits."""
    user = email_tokens.redeem(db, token, "confirm_email", now)
    if user is None or user.is_demo:
        return None
    user.email_verified_at = user.email_verified_at or now
    profile = profiles.get_or_create_profile(db, user)
    profile.digest_opted_in_at = now
    profile.digest_unsubscribed_at = None
    return user


def turn_off(db: Session, user: User, now: datetime) -> State:
    profile = profiles.get_or_create_profile(db, user)
    profile.digest_opted_in_at = None
    profile.digest_unsubscribed_at = now
    return state(db, user, now)


def set_day(db: Session, user: User, weekday: int, now: datetime) -> State:
    profiles.get_or_create_profile(db, user).digest_weekday = weekday
    return state(db, user, now)


def unsubscribe(db: Session, token: str, now: datetime) -> bool:
    """An unsubscribe link from an email, which works without logging in. False for a token
    that isn't genuine."""
    found = email_links.verify(token, "unsubscribe")
    if found is None:
        return False
    try:
        user = db.get(User, uuid.UUID(found))
    except ValueError:
        return False
    if user is None:
        # The account is gone, and with it every email: nothing left to stop.
        return True
    turn_off(db, user, now)
    return True


def subscribed(db: Session) -> list[User]:
    """Everyone the weekly email goes to: turned on, confirmed, and not a demo."""
    return list(
        db.scalars(
            select(User)
            .join(Profile, Profile.user_id == User.id)
            .where(
                Profile.digest_opted_in_at.is_not(None),
                User.email_verified_at.is_not(None),
                User.is_demo.is_(False),
            )
            .order_by(User.created_at)
        )
    )


def confirmation(user: User, token: str) -> Email:
    url = f"{get_settings().app_url}/confirm-email?token={token}"
    letter = Letter()
    letter.paragraph(
        "Follow this link to confirm this address and turn on WearWise's weekly email: the "
        "picks worth a look each week, judged against what you already own."
    )
    letter.link("Confirm my address", url)
    letter.small(
        "The link works once, for two days. If you didn't ask for this, ignore this email: "
        "nothing more will be sent."
    )
    text, html = letter.finish()
    return Email(
        to=user.email,
        subject="Confirm your address for WearWise's weekly email",
        text=text,
        html=html,
    )
