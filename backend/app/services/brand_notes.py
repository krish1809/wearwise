"""The person's notes on brands: which size fits, how the quality holds up, what it costs."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import BrandNote, User

# Notes are typed by hand, so this is far above real use. It keeps the list one small response.
MAX_NOTES = 200


class BrandNoteExists(Exception):
    """The person already has a note for this brand (ignoring capitals)."""


class TooManyBrandNotes(Exception):
    pass


def list_notes(db: Session, user: User) -> list[BrandNote]:
    query = select(BrandNote).where(BrandNote.user_id == user.id)
    return list(db.scalars(query.order_by(func.lower(BrandNote.brand))))


def find_note(db: Session, user: User, note_id: uuid.UUID) -> BrandNote | None:
    """The note, only if it belongs to this person."""
    query = select(BrandNote).where(BrandNote.id == note_id, BrandNote.user_id == user.id)
    return db.scalar(query)


def create_note(db: Session, user: User, fields: dict[str, Any]) -> BrandNote:
    count = db.scalar(select(func.count()).where(BrandNote.user_id == user.id)) or 0
    if count >= MAX_NOTES:
        raise TooManyBrandNotes
    note = BrandNote(user_id=user.id)
    _save(db, note, fields)
    return note


def update_note(db: Session, note: BrandNote, changes: dict[str, Any]) -> BrandNote:
    _save(db, note, changes)
    return note


def delete_note(db: Session, note: BrandNote) -> None:
    db.delete(note)
    db.flush()


def _save(db: Session, note: BrandNote, changes: dict[str, Any]) -> None:
    # The unique index on (user_id, lower(brand)) is the real check, so two saves at once can't
    # both get through. The savepoint keeps the rest of the request's work if it fires. Changes
    # are applied inside it because opening a savepoint first flushes anything pending.
    try:
        with db.begin_nested():
            for name, value in changes.items():
                setattr(note, name, value)
            db.add(note)
            db.flush()
    except IntegrityError as error:
        raise BrandNoteExists from error
