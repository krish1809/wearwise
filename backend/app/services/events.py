"""Events: a dated thing with a dress code ("Priya's wedding, festive"). An event sets its
day's occasion in the week's plan, over the usual occasion for that weekday."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, Occasion, User
from app.services import reference

EARLIEST = date(2000, 1, 1)


class EventInvalid(Exception):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Invalid event")
        self.fields = fields


def between(db: Session, user: User, start: date, end: date) -> list[Event]:
    """Events from start to end, inclusive, by day."""
    return list(
        db.scalars(
            select(Event)
            .where(Event.user_id == user.id, Event.day >= start, Event.day <= end)
            .order_by(Event.day, Event.created_at, Event.id)
        )
    )


def find(db: Session, user: User, event_id: uuid.UUID) -> Event | None:
    return db.scalar(select(Event).where(Event.id == event_id, Event.user_id == user.id))


def create(db: Session, user: User, fields: dict[str, Any]) -> Event:
    _check(db, fields)
    event = Event(user_id=user.id, **fields)
    db.add(event)
    db.flush()
    return event


def update(db: Session, event: Event, changes: dict[str, Any]) -> None:
    _check(db, changes)
    for name, value in changes.items():
        setattr(event, name, value)
    db.flush()


def delete(db: Session, event: Event) -> None:
    db.delete(event)
    db.flush()


def _check(db: Session, fields: dict[str, Any]) -> None:
    problems = {}
    if "day" in fields and fields["day"] < EARLIEST:
        problems["day"] = "Choose a day from 2000 onwards."
    if "occasion_id" in fields and fields["occasion_id"] not in reference.known_ids(db, Occasion):
        problems["occasion_id"] = "Choose one of the options shown."
    if problems:
        raise EventInvalid(problems)
