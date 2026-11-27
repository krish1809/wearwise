"""The weekly email's settings (docs/AGENTS.md, section 7): on (after confirming the address),
off, and which day."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, EmailDep, SessionDep
from app.api.errors import ApiError, error_responses
from app.services import rate_limit, subscriptions

router = APIRouter(prefix="/digest-settings", tags=["digests"])

# Turning it on can send a confirmation email, so it's limited.
TURN_ON_PER_USER = rate_limit.Limit(attempts=5, window=timedelta(hours=1))


class DigestSettingsOut(BaseModel):
    on: bool
    waiting_for_confirmation: bool
    # 0 (Monday) to 6 (Sunday).
    weekday: int
    email: str
    confirmed: bool
    # Email goes only to listed addresses for now, and this one isn't listed.
    preview_only: bool


class DigestTurnOn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday: int | None = Field(default=None, ge=0, le=6)


class DigestDayChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday: int = Field(ge=0, le=6)


def _out(found: subscriptions.State) -> DigestSettingsOut:
    return DigestSettingsOut(**vars(found))


@router.get("", response_model=DigestSettingsOut, responses=error_responses(401))
def get_digest_settings(user: CurrentUser, db: SessionDep) -> DigestSettingsOut:
    return _out(subscriptions.state(db, user, datetime.now(UTC)))


@router.patch("", response_model=DigestSettingsOut, responses=error_responses(401, 403, 422))
def change_digest_day(
    body: DigestDayChange, user: CurrentUser, db: SessionDep
) -> DigestSettingsOut:
    found = subscriptions.set_day(db, user, body.weekday, datetime.now(UTC))
    db.commit()
    return _out(found)


@router.post(
    "/on", response_model=DigestSettingsOut, responses=error_responses(401, 403, 409, 422, 429)
)
def turn_digest_on(
    body: DigestTurnOn, user: CurrentUser, db: SessionDep, sender: EmailDep
) -> DigestSettingsOut:
    """On at once for a confirmed address; otherwise a confirmation link is sent first."""
    try:
        rate_limit.hit(db, f"digest-on:user:{user.id}", TURN_ON_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(429, "rate_limited", "Too many tries. Try again in an hour.") from error
    try:
        found = subscriptions.turn_on(db, user, sender, datetime.now(UTC), body.weekday)
    except subscriptions.DemoAccount as error:
        db.commit()
        raise ApiError(
            409, "demo_account", "A demo account can't get email. Make your own account first."
        ) from error
    except subscriptions.PreviewOnly as error:
        db.commit()
        raise ApiError(
            409,
            "email_preview_only",
            "For now the weekly email goes only to the owner's address. Your picks are on the "
            "Weekly picks page.",
        ) from error
    db.commit()
    return _out(found)


@router.post("/off", response_model=DigestSettingsOut, responses=error_responses(401, 403))
def turn_digest_off(user: CurrentUser, db: SessionDep) -> DigestSettingsOut:
    found = subscriptions.turn_off(db, user, datetime.now(UTC))
    db.commit()
    return _out(found)
