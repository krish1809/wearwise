"""The wear log: what the person wore, and when. Every wear count comes from these rows.

Logging an outfit copies its pieces into the log, so editing the outfit later doesn't change
history. Each item's `wears_since_wash` is recounted from the log whenever the log changes:
wears on days after its last wash. Recounting rather than adding one keeps the number right
when a log is edited, deleted, or added for an earlier day.
"""

import base64
import binascii
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.models import Item, Occasion, Outfit, OutfitItem, User, WearLog, WearLogItem
from app.services import reference
from app.services.item_names import ItemNames

# Phones are often ahead of the server's UTC date (India by five and a half hours), so
# "today" may be tomorrow for the server.
FUTURE_SLACK = timedelta(days=1)
EARLIEST = date(2000, 1, 1)


class WearInvalid(Exception):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Invalid wear log")
        self.fields = fields


class BadCursor(Exception):
    pass


@dataclass(frozen=True)
class ItemWear:
    count: int
    last_worn_on: date | None


@dataclass
class Page:
    logs: list[WearLog]
    next_cursor: str | None


def today() -> date:
    return datetime.now(UTC).date()


def log_wear(
    db: Session,
    user: User,
    *,
    worn_on: date,
    outfit_id: uuid.UUID | None,
    item_ids: list[uuid.UUID] | None,
    occasion_id: str | None,
    note: str | None,
) -> tuple[WearLog, bool]:
    """Record a wear of an outfit or of loose items. Returns the log and whether it's new:
    logging the same outfit twice for one day returns the first log, so a double tap is safe."""
    problems = _check_common(db, worn_on, occasion_id)
    outfit = None
    if outfit_id is not None:
        if item_ids:
            problems["item_ids"] = "Log an outfit or some items, not both."
        outfit = db.scalar(select(Outfit).where(Outfit.id == outfit_id, Outfit.user_id == user.id))
        if outfit is None:
            problems["outfit_id"] = "That outfit doesn't exist."
    elif not item_ids:
        problems["item_ids"] = "Choose at least one item you wore."
    pieces: list[tuple[Item, str]] = []
    if outfit is not None and not problems:
        rows = db.execute(
            select(Item, OutfitItem.slot)
            .join(OutfitItem, OutfitItem.item_id == Item.id)
            .where(OutfitItem.outfit_id == outfit.id)
        ).all()
        pieces = [(item, slot) for item, slot in rows]
        if not pieces:
            problems["outfit_id"] = "Every piece of that outfit has been deleted."
    elif item_ids and not problems:
        found = _owned_items(db, user, item_ids)
        if len(found) != len(set(item_ids)):
            problems["item_ids"] = "Some of those items don't exist."
        pieces = [(item, item.slot) for item in found]
    if problems:
        raise WearInvalid(problems)

    if outfit is not None:
        existing = db.scalar(
            select(WearLog).where(
                WearLog.user_id == user.id,
                WearLog.outfit_id == outfit.id,
                WearLog.worn_on == worn_on,
            )
        )
        if existing is not None:
            return existing, False

    log = WearLog(
        user_id=user.id,
        worn_on=worn_on,
        outfit_id=outfit.id if outfit else None,
        occasion_id=occasion_id if occasion_id else (outfit.occasion_id if outfit else None),
        note=note,
    )
    db.add(log)
    db.flush()
    _write_pieces(db, user, log, pieces)
    recount(db, [item.id for item, _ in pieces])
    return log, True


def update_log(db: Session, user: User, log: WearLog, changes: dict[str, Any]) -> None:
    """Change the day, occasion, note, or (for loose items) which items were worn."""
    changes = dict(changes)
    problems = _check_common(
        db, changes.get("worn_on", log.worn_on), changes.get("occasion_id", log.occasion_id)
    )
    if changes.get("worn_on") is None:
        changes.pop("worn_on", None)
    new_items = changes.pop("item_ids", None)
    pieces: list[tuple[Item, str]] | None = None
    if new_items is not None:
        if not new_items:
            problems["item_ids"] = "Choose at least one item you wore."
        else:
            found = _owned_items(db, user, new_items)
            if len(found) != len(set(new_items)):
                problems["item_ids"] = "Some of those items don't exist."
            pieces = [(item, item.slot) for item in found]
    if problems:
        raise WearInvalid(problems)

    affected = set(_item_ids_in(db, log))
    for name, value in changes.items():
        setattr(log, name, value)
    if pieces is not None:
        db.execute(delete(WearLogItem).where(WearLogItem.wear_log_id == log.id))
        _write_pieces(db, user, log, pieces)
        affected |= {item.id for item, _ in pieces}
    db.flush()
    recount(db, list(affected))


def delete_log(db: Session, log: WearLog) -> None:
    affected = _item_ids_in(db, log)
    db.delete(log)
    db.flush()
    recount(db, affected)


def find_log(db: Session, user: User, log_id: uuid.UUID) -> WearLog | None:
    return db.scalar(select(WearLog).where(WearLog.id == log_id, WearLog.user_id == user.id))


def list_logs(
    db: Session,
    user: User,
    *,
    item_id: uuid.UUID | None,
    outfit_id: uuid.UUID | None,
    on: date | None,
    limit: int,
    cursor: str | None,
) -> Page:
    """Newest first: by day, then by when it was logged."""
    query = select(WearLog).where(WearLog.user_id == user.id)
    if item_id is not None:
        query = query.where(
            WearLog.id.in_(select(WearLogItem.wear_log_id).where(WearLogItem.item_id == item_id))
        )
    if outfit_id is not None:
        query = query.where(WearLog.outfit_id == outfit_id)
    if on is not None:
        query = query.where(WearLog.worn_on == on)
    if cursor:
        worn_on, created, log_id = _decode(cursor)
        query = query.where(
            or_(
                WearLog.worn_on < worn_on,
                and_(
                    WearLog.worn_on == worn_on,
                    or_(
                        WearLog.created_at < created,
                        and_(WearLog.created_at == created, WearLog.id < log_id),
                    ),
                ),
            )
        )
    query = query.order_by(WearLog.worn_on.desc(), WearLog.created_at.desc(), WearLog.id.desc())
    rows = list(db.scalars(query.limit(limit + 1)))
    page = rows[:limit]
    next_cursor = _encode(page[-1]) if len(rows) > limit and page else None
    return Page(logs=page, next_cursor=next_cursor)


def pieces_of(db: Session, log_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[WearLogItem]]:
    found: dict[uuid.UUID, list[WearLogItem]] = {log_id: [] for log_id in log_ids}
    if log_ids:
        for row in db.scalars(select(WearLogItem).where(WearLogItem.wear_log_id.in_(log_ids))):
            found[row.wear_log_id].append(row)
    return found


def item_wear(db: Session, item_ids: list[uuid.UUID]) -> dict[uuid.UUID, ItemWear]:
    """How often, and when last, each item was worn."""
    if not item_ids:
        return {}
    rows = db.execute(
        select(WearLogItem.item_id, func.count(), func.max(WearLog.worn_on))
        .join(WearLog, WearLog.id == WearLogItem.wear_log_id)
        .where(WearLogItem.item_id.in_(item_ids))
        .group_by(WearLogItem.item_id)
    ).all()
    return {item_id: ItemWear(count, last) for item_id, count, last in rows if item_id}


def outfit_wear(db: Session, outfit_ids: list[uuid.UUID]) -> dict[uuid.UUID, ItemWear]:
    """How often, and when last, each outfit was logged as worn."""
    if not outfit_ids:
        return {}
    rows = db.execute(
        select(WearLog.outfit_id, func.count(), func.max(WearLog.worn_on))
        .where(WearLog.outfit_id.in_(outfit_ids))
        .group_by(WearLog.outfit_id)
    ).all()
    return {outfit_id: ItemWear(count, last) for outfit_id, count, last in rows if outfit_id}


def recount(db: Session, item_ids: Iterable[uuid.UUID]) -> None:
    """Set each item's wears since its last wash from the log."""
    ids = list(set(item_ids))
    if not ids:
        return
    for item in db.scalars(select(Item).where(Item.id.in_(ids))):
        query = (
            select(func.count())
            .select_from(WearLogItem)
            .join(WearLog, WearLog.id == WearLogItem.wear_log_id)
            .where(WearLogItem.item_id == item.id)
        )
        if item.last_washed_on is not None:
            query = query.where(WearLog.worn_on > item.last_washed_on)
        item.wears_since_wash = min(db.scalar(query) or 0, 32767)
    db.flush()


def mark_washed(db: Session, item: Item, on: date) -> None:
    """The item is clean again: wears on this day or before no longer count."""
    item.last_washed_on = on
    db.flush()
    recount(db, [item.id])


def _check_common(db: Session, worn_on: date, occasion_id: str | None) -> dict[str, str]:
    problems: dict[str, str] = {}
    if worn_on > today() + FUTURE_SLACK:
        problems["worn_on"] = "That day hasn't happened yet."
    elif worn_on < EARLIEST:
        problems["worn_on"] = "Choose a day from 2000 onwards."
    if occasion_id is not None and occasion_id not in reference.known_ids(db, Occasion):
        problems["occasion_id"] = "Choose one of the options shown."
    return problems


def _owned_items(db: Session, user: User, item_ids: list[uuid.UUID]) -> list[Item]:
    query = select(Item).where(Item.user_id == user.id, Item.id.in_(set(item_ids)))
    return list(db.scalars(query))


def _write_pieces(db: Session, user: User, log: WearLog, pieces: list[tuple[Item, str]]) -> None:
    names = ItemNames(db, user)
    for item, slot in pieces:
        db.add(
            WearLogItem(
                wear_log_id=log.id, item_id=item.id, slot=slot, item_name=names.display_name(item)
            )
        )
    db.flush()


def _item_ids_in(db: Session, log: WearLog) -> list[uuid.UUID]:
    query = select(WearLogItem.item_id).where(WearLogItem.wear_log_id == log.id)
    return [item_id for item_id in db.scalars(query) if item_id is not None]


def _encode(log: WearLog) -> str:
    raw = json.dumps([log.worn_on.isoformat(), log.created_at.isoformat(), str(log.id)])
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode(cursor: str) -> tuple[date, datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        worn_on, created, log_id = json.loads(raw)
        return date.fromisoformat(worn_on), datetime.fromisoformat(created), uuid.UUID(log_id)
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError) as error:
        raise BadCursor from error
