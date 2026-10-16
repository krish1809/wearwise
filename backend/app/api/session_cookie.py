"""The session cookie. httpOnly keeps it away from page scripts; SameSite=Lax keeps it off
requests other sites start. It's first-party because the browser only ever talks to the
frontend's domain, which forwards /api/* here."""

from fastapi import Response

from app.core.config import Settings

SESSION_COOKIE = "wearwise_session"


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_days * 24 * 60 * 60,
        httponly=True,
        # Local development runs over plain http, where a Secure cookie wouldn't be sent back.
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )


def clear_session_cookie_headers(settings: Settings) -> dict[str, str]:
    """The Set-Cookie header that removes the cookie, for error responses."""
    response = Response()
    clear_session_cookie(response, settings)
    return {"set-cookie": response.headers["set-cookie"]}
