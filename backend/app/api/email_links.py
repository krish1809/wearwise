"""What the links in WearWise's emails do, without logging in (D57): unsubscribe, and "not for
me" on a pick. Each is guarded by the signed token in its link.

The pages these links open call `router`'s routes, which need the app's usual custom header like
every other change. Mail apps' one-click unsubscribe button (RFC 8058) posts straight to
`one_click` from the mail provider's servers, without that header or any cookie, so `one_click` is
mounted outside the header check; its signed token is what guards it.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import SessionDep, client_ip
from app.api.errors import ApiError, error_responses
from app.services import digests, rate_limit, subscriptions

router = APIRouter(prefix="/email", tags=["email"])
one_click = APIRouter(prefix="/api/v1/email", tags=["email"])

LINKS_PER_IP = rate_limit.Limit(attempts=30, window=timedelta(hours=1))


class EmailLinkToken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(max_length=500)


def _limited(db: Session, request: Request) -> None:
    try:
        rate_limit.hit(db, f"email-links:ip:{client_ip(request)}", LINKS_PER_IP)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(429, "rate_limited", "Too many tries. Try again later.") from error


def _expired() -> ApiError:
    return ApiError(400, "link_expired", "That link doesn't work. Ask for a new one.")


@router.post(
    "/unsubscribe",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(400, 403, 422, 429),
)
def unsubscribe(body: EmailLinkToken, request: Request, db: SessionDep) -> None:
    """The unsubscribe link in an email: the weekly email stops."""
    _limited(db, request)
    if not subscriptions.unsubscribe(db, body.token, datetime.now(UTC)):
        db.commit()
        raise _expired()
    db.commit()


@router.post(
    "/not-for-me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(400, 403, 422, 429),
)
def not_for_me_by_link(body: EmailLinkToken, request: Request, db: SessionDep) -> None:
    """ "Not for me" on a pick, from its link in an email."""
    _limited(db, request)
    if digests.react_by_link(db, body.token, datetime.now(UTC)) is None:
        db.commit()
        raise _expired()
    db.commit()


@one_click.post(
    "/unsubscribe/one-click",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(400, 429),
)
def unsubscribe_one_click(token: str, request: Request, db: SessionDep) -> None:
    """A mail app's unsubscribe button: it posts here with the token from the email's
    List-Unsubscribe header."""
    _limited(db, request)
    if not subscriptions.unsubscribe(db, token[:500], datetime.now(UTC)):
        db.commit()
        raise _expired()
    db.commit()
