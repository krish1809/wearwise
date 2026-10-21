"""Running the app: the browser's error reports, and the owner's page of counts."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, SessionDep, SettingsDep, client_ip
from app.api.errors import ApiError, error_responses
from app.services import ops, rate_limit, wear

# Open to anyone (errors happen before logging in too), so limited by address.
reports = APIRouter(tags=["ops"])
# For the accounts in ADMIN_EMAILS; everyone else gets the same 404 as a page that isn't there.
admin = APIRouter(prefix="/admin", tags=["ops"])

REPORTS_PER_IP = rate_limit.Limit(attempts=30, window=timedelta(hours=1))


class BrowserError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(max_length=2000)
    # The page's path; anything after ? or # is dropped before it's stored.
    path: str = Field(max_length=500)
    stack: str | None = Field(default=None, max_length=10_000)


@reports.post(
    "/client-errors",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(403, 422, 429),
)
def report_browser_error(body: BrowserError, request: Request, db: SessionDep) -> None:
    """Something broke in the browser: recorded for the owner, without the account."""
    try:
        rate_limit.hit(db, f"client-errors:ip:{client_ip(request)}", REPORTS_PER_IP)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(429, "rate_limited", "Too many reports.") from error
    ops.add_error(
        db,
        source="browser",
        request_id=None,
        method=None,
        path=body.path.split("?")[0].split("#")[0],
        status=None,
        kind="browser",
        message=body.message,
        detail=body.stack,
    )
    db.commit()


class AcceptanceOut(BaseModel):
    engine_version: str
    shown: int
    liked: int
    saved: int
    worn: int
    accepted: int


class ErrorOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    source: str
    request_id: str | None
    method: str | None
    path: str | None
    status: int | None
    kind: str
    message: str


class StatsOut(BaseModel):
    users: int
    new_users_7d: int
    demo_users: int
    items: int
    photos: int
    outfits: int
    wear_logs: int
    wear_logs_7d: int
    # Suggestions shown in the last 30 days, by engine version, and what people did with them.
    acceptance: list[AcceptanceOut]
    ai_messages_today: int
    ai_images_today: int
    ai_spend_today_usd: float
    ai_daily_cap_usd: float
    errors_24h: dict[str, int]
    recent_errors: list[ErrorOut]


@admin.get("/stats", response_model=StatsOut, responses=error_responses(401, 404))
def get_stats(user: CurrentUser, db: SessionDep, settings: SettingsDep) -> StatsOut:
    """Counts for the owner, straight from the tables."""
    if user.email not in settings.admins:
        raise ApiError(404, "not_found", "Not Found")
    found = ops.stats(db, wear.today())
    return StatsOut(
        users=found.users,
        new_users_7d=found.new_users_7d,
        demo_users=found.demo_users,
        items=found.items,
        photos=found.photos,
        outfits=found.outfits,
        wear_logs=found.wear_logs,
        wear_logs_7d=found.wear_logs_7d,
        acceptance=[AcceptanceOut(**vars(row)) for row in found.acceptance],
        ai_messages_today=found.ai_messages_today,
        ai_images_today=found.ai_images_today,
        ai_spend_today_usd=found.ai_spend_today_micro_usd / 1_000_000,
        ai_daily_cap_usd=settings.ai_daily_spend_cap_usd,
        errors_24h=found.errors_24h,
        recent_errors=[
            ErrorOut.model_validate(e, from_attributes=True) for e in found.recent_errors
        ],
    )
