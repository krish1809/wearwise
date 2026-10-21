"""Running the app: errors recorded for the owner, and the owner's page of counts.

Errors carry no account, and go after 30 days. Counts come straight from the tables.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.db import get_sessionmaker
from app.models import (
    AIUsage,
    ErrorEvent,
    Item,
    ItemImage,
    Outfit,
    Suggestion,
    User,
    WearLog,
)

log = logging.getLogger(__name__)

KEPT_FOR = timedelta(days=30)
MESSAGE = 500
DETAIL = 4000
RECENT = 20


def add_error(db: Session, **fields: object) -> None:
    """Record an error, shortened to fit, and drop any over 30 days old."""
    for name, limit in (("message", MESSAGE), ("path", 300)):
        value = fields.get(name)
        if isinstance(value, str):
            fields[name] = value[:limit]
    # A stack trace keeps its end: the line that failed and the error come last.
    detail = fields.get("detail")
    if isinstance(detail, str) and len(detail) > DETAIL:
        fields["detail"] = "…" + detail[-DETAIL:]
    db.add(ErrorEvent(**fields))
    db.execute(delete(ErrorEvent).where(ErrorEvent.created_at < datetime.now(UTC) - KEPT_FOR))
    db.flush()


def record_server_error(**fields: object) -> None:
    """From the middleware, after a request failed: its own session, since the request's may
    be what broke. Never raises: a failure to record mustn't hide the error itself."""
    try:
        with get_sessionmaker()() as db:
            add_error(db, source="server", **fields)
            db.commit()
    except Exception:
        log.exception("Couldn't record an error")


@dataclass(frozen=True)
class EngineAcceptance:
    engine_version: str
    shown: int
    liked: int
    saved: int
    worn: int
    # Liked, saved, or worn (each suggestion counted once).
    accepted: int


@dataclass(frozen=True)
class Stats:
    users: int
    new_users_7d: int
    demo_users: int
    items: int
    photos: int
    outfits: int
    wear_logs: int
    wear_logs_7d: int
    acceptance: list[EngineAcceptance]
    ai_messages_today: int
    ai_images_today: int
    ai_spend_today_micro_usd: int
    errors_24h: dict[str, int]
    recent_errors: list[ErrorEvent]


def stats(db: Session, today: date) -> Stats:
    now = datetime.now(UTC)
    week = now - timedelta(days=7)
    real = User.is_demo.is_(False)
    count = func.count()
    acceptance = [
        EngineAcceptance(*row)
        for row in db.execute(
            select(
                Suggestion.engine_version,
                count,
                func.count().filter(Suggestion.rating == "like"),
                func.count().filter(Suggestion.saved_outfit_id.is_not(None)),
                func.count().filter(Suggestion.wear_log_id.is_not(None)),
                func.count().filter(
                    (Suggestion.rating == "like")
                    | Suggestion.saved_outfit_id.is_not(None)
                    | Suggestion.wear_log_id.is_not(None)
                ),
            )
            .where(Suggestion.created_at >= now - timedelta(days=30))
            .group_by(Suggestion.engine_version)
            .order_by(Suggestion.engine_version.desc())
        )
    ]
    usage = db.execute(
        select(
            func.coalesce(func.sum(AIUsage.messages), 0),
            func.coalesce(func.sum(AIUsage.images), 0),
            func.coalesce(func.sum(AIUsage.cost_micro_usd), 0),
        ).where(AIUsage.day == today)
    ).one()
    errors = dict(
        db.execute(
            select(ErrorEvent.source, count)
            .where(ErrorEvent.created_at >= now - timedelta(days=1))
            .group_by(ErrorEvent.source)
        ).all()
    )
    return Stats(
        users=db.scalar(select(count).where(real).select_from(User)) or 0,
        new_users_7d=db.scalar(select(count).where(real, User.created_at >= week)) or 0,
        demo_users=db.scalar(select(count).where(User.is_demo).select_from(User)) or 0,
        items=db.scalar(select(count).select_from(Item).where(Item.archived_at.is_(None))) or 0,
        photos=db.scalar(select(count).select_from(ItemImage)) or 0,
        outfits=db.scalar(select(count).select_from(Outfit)) or 0,
        wear_logs=db.scalar(select(count).select_from(WearLog)) or 0,
        wear_logs_7d=db.scalar(select(count).select_from(WearLog).where(WearLog.created_at >= week))
        or 0,
        acceptance=acceptance,
        ai_messages_today=int(usage[0]),
        ai_images_today=int(usage[1]),
        ai_spend_today_micro_usd=int(usage[2]),
        errors_24h={"server": errors.get("server", 0), "browser": errors.get("browser", 0)},
        recent_errors=list(
            db.scalars(select(ErrorEvent).order_by(ErrorEvent.created_at.desc()).limit(RECENT))
        ),
    )
