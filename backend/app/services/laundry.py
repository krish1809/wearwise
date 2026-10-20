"""The laundry: what's in the wash or due one, and marking it clean again."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Item, User
from app.services import wear


class LaundryInvalid(Exception):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Invalid laundry")
        self.fields = fields


def pending(db: Session, user: User) -> list[Item]:
    """Items in the laundry, then items worn as often as they go between washes."""
    rows = db.scalars(
        select(Item).where(
            Item.user_id == user.id,
            Item.archived_at.is_(None),
            or_(
                Item.status == "laundry",
                (Item.status == "available")
                & Item.wears_before_wash.is_not(None)
                & (Item.wears_since_wash >= Item.wears_before_wash),
            ),
        )
    )
    return sorted(rows, key=lambda item: (item.status != "laundry", item.created_at, item.id))


def done(db: Session, user: User, item_ids: list[uuid.UUID]) -> None:
    """Clean again: back to available, and earlier wears stop counting towards the next
    wash (the same as moving an item out of the laundry on its page)."""
    unique = list(dict.fromkeys(item_ids))
    found = list(
        db.scalars(
            select(Item).where(
                Item.user_id == user.id, Item.id.in_(unique), Item.archived_at.is_(None)
            )
        )
    )
    if len(found) != len(unique):
        raise LaundryInvalid({"item_ids": "Some of those items don't exist."})
    today = wear.today()
    for item in found:
        if item.status == "laundry":
            item.status = "available"
        wear.mark_washed(db, item, today)
    db.flush()
