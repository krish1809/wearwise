"""Dependencies that routes declare in their signatures."""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.adapters.ai import AIProvider, get_ai
from app.adapters.products import PageReader, get_page_reader
from app.adapters.storage import Storage, get_storage
from app.adapters.weather import WeatherProvider, get_weather
from app.api.errors import ApiError
from app.api.session_cookie import SESSION_COOKIE, clear_session_cookie_headers
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.models.user import User
from app.services import auth, rate_limit

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
StorageDep = Annotated[Storage, Depends(get_storage)]
WeatherDep = Annotated[WeatherProvider, Depends(get_weather)]
PagesDep = Annotated[PageReader, Depends(get_page_reader)]
# None when AI features are off.
AIDep = Annotated[AIProvider | None, Depends(get_ai)]


def get_current_user(request: Request, db: SessionDep, settings: SettingsDep) -> User:
    """The logged-in user, from the session cookie. Every route with user data depends on this."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise ApiError(401, "not_authenticated", "Log in to continue.")
    user = auth.user_for_session(db, token, days=settings.session_days)
    db.commit()  # keeps a refreshed expiry, or removes an expired session
    if user is None:
        # Remove the stale cookie too, so the website stops treating the person as logged in.
        raise ApiError(
            401,
            "session_expired",
            "Your session has ended. Log in again.",
            headers=clear_session_cookie_headers(settings),
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def client_ip(request: Request) -> str:
    # On Render, uvicorn's --proxy-headers sets this from X-Forwarded-For.
    return request.client.host if request.client else "unknown"


_STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}


def require_requested_with(request: Request) -> None:
    """Block forged requests (CSRF): other sites' forms can't add a custom header."""
    if request.method in _STATE_CHANGING and not request.headers.get("x-requested-with"):
        raise ApiError(
            403, "missing_header", "Requests that change data need an X-Requested-With header."
        )


# Every change a person makes counts against one budget, far above what anyone does by hand,
# so a script can't fill the database. The costly routes have tighter limits of their own.
WRITES_PER_USER = rate_limit.Limit(attempts=1000, window=timedelta(hours=1))


def write_budget(request: Request, user: CurrentUser, db: SessionDep) -> None:
    if request.method not in _STATE_CHANGING:
        return
    try:
        rate_limit.hit(db, f"writes:user:{user.id}", WRITES_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        minutes = max(1, round(error.retry_after_seconds / 60))
        raise ApiError(
            429,
            "rate_limited",
            f"That's a lot of changes in an hour. Try again in {minutes} minutes.",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    db.commit()
