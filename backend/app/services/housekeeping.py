"""Tidying that would otherwise wait for someone to come back: visitors' demo accounts over a
day old, photos never saved with anything, old error reports, old rate-limit counts, and ended
sessions.

Run when the server starts (the free server sleeps when idle, so it starts often) and safe to
run any time: it only removes what has expired.
"""

from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult, Delete, delete
from sqlalchemy.orm import Session

from app.models import ErrorEvent, RateLimitHit, UserSession
from app.services import demo, ops, photos, rate_limit

BATCH = 500


def tidy(db: Session, now: datetime) -> tuple[dict[str, int], list[str]]:
    """Remove what has expired. Returns counts, and photo files to delete once committed."""
    demos, keys = demo.remove_expired(db, now, limit=BATCH)
    unsaved = photos.remove_unattached(db, limit=BATCH)
    counts = {
        "demo accounts": demos,
        "unsaved photos": len(unsaved) // 2,
        "error reports": _deleted(
            db, delete(ErrorEvent).where(ErrorEvent.created_at < now - ops.KEPT_FOR)
        ),
        "rate-limit counts": _deleted(
            db, delete(RateLimitHit).where(RateLimitHit.window_start < now - rate_limit.KEPT_FOR)
        ),
        "ended sessions": _deleted(db, delete(UserSession).where(UserSession.expires_at < now)),
    }
    db.flush()
    return counts, keys + unsaved


def _deleted(db: Session, statement: Delete) -> int:
    return cast(CursorResult[Any], db.execute(statement)).rowcount
