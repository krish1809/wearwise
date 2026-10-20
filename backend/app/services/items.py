"""Wardrobe items: add, change, archive, delete, find, and link into matching sets.

Every query filters by the person. Functions that remove photos return their storage keys, so
the caller deletes the files only after the database change is committed.
"""

import base64
import binascii
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.models import Category, ColorFamily, Item, ItemImage, Occasion, User
from app.services import categories, photos, reference, wear

Sort = Literal["newest", "oldest", "category"]

# A suit, a co-ord, a kurta set: sets are small.
MAX_SET_SIZE = 6

UNKNOWN_CHOICE = "Choose one of the options shown."

# Fields every item must keep; null is refused for these.
REQUIRED = {"category_id", "color_primary", "pattern", "formality", "warmth", "status"}


class ItemInvalid(Exception):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Invalid item")
        self.fields = fields


class SetTooLarge(Exception):
    pass


class BadCursor(Exception):
    pass


@dataclass
class Filters:
    q: str = ""
    groups: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    slots: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    seasons: list[str] = field(default_factory=list)
    occasions: list[str] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    archived: bool = False


@dataclass
class Page:
    items: list[Item]
    next_cursor: str | None
    total: int


def find_item(db: Session, user: User, item_id: uuid.UUID) -> Item | None:
    return db.scalar(select(Item).where(Item.id == item_id, Item.user_id == user.id))


def create_item(db: Session, user: User, fields: dict[str, Any]) -> Item:
    """Add an item. Formality, warmth, and wash count start from the category's defaults."""
    fields = dict(fields)
    photo_id = fields.pop("photo_id", None)
    category = categories.find_category(db, user, fields.get("category_id") or "")
    problems = check_fields(db, user, fields)
    if category is None:
        problems["category_id"] = UNKNOWN_CHOICE
    photo = usable_photo(db, user, photo_id, problems)
    if problems or category is None:
        raise ItemInvalid(problems)

    if fields.get("formality") is None:
        fields["formality"] = category.formality_default
    if fields.get("warmth") is None:
        fields["warmth"] = category.warmth
    # Sent as null, it means "not washed on a schedule"; left out, the category decides.
    if "wears_before_wash" not in fields:
        fields["wears_before_wash"] = category.wears_before_wash
    for name in ("pattern", "status"):
        if fields.get(name) is None:
            fields.pop(name, None)  # the column defaults: solid, available
    if photo is not None and not fields.get("color_hex"):
        fields["color_hex"] = photo.dominant_hex
    item = Item(user_id=user.id, slot=category.slot, **fields)
    db.add(item)
    db.flush()
    if photo is not None:
        photo.item_id = item.id
    _changed(user)
    db.flush()
    return item


def update_item(db: Session, user: User, item: Item, changes: dict[str, Any]) -> list[str]:
    """Apply only the fields given; null clears an optional one. Returns storage keys to delete
    (a replaced or removed photo)."""
    changes = dict(changes)
    problems = {
        name: "This can't be empty."
        for name in REQUIRED
        if name in changes and changes[name] is None
    }
    for name in problems:
        del changes[name]
    problems.update(check_fields(db, user, changes))
    category = None
    if "category_id" in changes:
        category = categories.find_category(db, user, changes["category_id"])
        if category is None:
            problems["category_id"] = UNKNOWN_CHOICE
    replacing_photo = "photo_id" in changes
    new_photo_id = changes.pop("photo_id", None)
    new_photo = usable_photo(db, user, new_photo_id, problems) if new_photo_id else None
    if problems:
        raise ItemInvalid(problems)

    if category is not None:
        item.slot = category.slot
    back_from_laundry = changes.get("status") == "available" and item.status == "laundry"
    for name, value in changes.items():
        setattr(item, name, value)
    if back_from_laundry:
        # Clean again: earlier wears stop counting towards the next wash.
        wear.mark_washed(db, item, wear.today())

    keys: list[str] = []
    if replacing_photo:
        for old in db.scalars(select(ItemImage).where(ItemImage.item_id == item.id)):
            keys += [old.storage_key, old.thumb_key]
            db.delete(old)
        if new_photo is not None:
            new_photo.item_id = item.id
    _changed(user)
    db.flush()
    return keys


def set_archived(db: Session, user: User, item: Item, archived: bool) -> None:
    item.archived_at = datetime.now(UTC) if archived else None
    _changed(user)
    db.flush()


def delete_item(db: Session, user: User, item: Item) -> list[str]:
    """Delete the item and its photo rows. Returns the photo files to delete afterwards."""
    images = list(db.scalars(select(ItemImage).where(ItemImage.item_id == item.id)))
    keys = [key for image in images for key in (image.storage_key, image.thumb_key)]
    set_id = item.set_id
    db.delete(item)
    db.flush()
    if set_id is not None:
        _dissolve_if_single(db, user, set_id)
    _changed(user)
    db.flush()
    return keys


def link_set(db: Session, user: User, item: Item, other: Item) -> None:
    """Put two items in the same matching set, merging sets if both were in one."""
    target = item.set_id or other.set_id or uuid.uuid7()
    existing = {s for s in (item.set_id, other.set_id) if s is not None}
    members = {item.id, other.id}
    if existing:
        query = select(Item.id).where(Item.user_id == user.id, Item.set_id.in_(existing))
        members |= set(db.scalars(query))
    if len(members) > MAX_SET_SIZE:
        raise SetTooLarge
    db.execute(
        update(Item).where(Item.user_id == user.id, Item.id.in_(members)).values(set_id=target)
    )
    _changed(user)
    db.flush()
    db.refresh(item)


def unlink_set(db: Session, user: User, item: Item) -> None:
    set_id = item.set_id
    if set_id is None:
        return
    item.set_id = None
    db.flush()
    _dissolve_if_single(db, user, set_id)
    _changed(user)
    db.flush()


def set_members(db: Session, user: User, item: Item) -> list[Item]:
    if item.set_id is None:
        return []
    query = select(Item).where(
        Item.user_id == user.id, Item.set_id == item.set_id, Item.id != item.id
    )
    return list(db.scalars(query.order_by(Item.created_at)))


def primary_photos(db: Session, item_ids: list[uuid.UUID]) -> dict[uuid.UUID, ItemImage]:
    if not item_ids:
        return {}
    query = select(ItemImage).where(ItemImage.item_id.in_(item_ids), ItemImage.is_primary)
    return {image.item_id: image for image in db.scalars(query) if image.item_id}


def list_items(
    db: Session, user: User, filters: Filters, sort: Sort, limit: int, cursor: str | None
) -> Page:
    query = select(Item).join(Category, Category.id == Item.category_id)
    query = _filtered(query, user, filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    if sort == "category":
        query = query.order_by(Category.position, Item.created_at.desc(), Item.id.desc())
    elif sort == "oldest":
        query = query.order_by(Item.created_at, Item.id)
    else:
        query = query.order_by(Item.created_at.desc(), Item.id.desc())
    if cursor:
        query = query.where(_after(sort, _decode(cursor, sort)))

    rows = list(db.scalars(query.limit(limit + 1)))
    page, more = rows[:limit], len(rows) > limit
    next_cursor = None
    if more and page:
        last = page[-1]
        position = None
        if sort == "category":
            position = db.scalar(select(Category.position).where(Category.id == last.category_id))
        next_cursor = _encode(sort, last, position)
    return Page(items=page, next_cursor=next_cursor, total=total)


def _filtered(query: Select[Item], user: User, f: Filters) -> Select[Item]:
    query = query.where(Item.user_id == user.id)
    query = query.where(Item.archived_at.is_not(None) if f.archived else Item.archived_at.is_(None))
    words = f.q.split()
    if words:
        colour = (
            select(ColorFamily.name).where(ColorFamily.id == Item.color_primary).scalar_subquery()
        )
        searchable = func.concat_ws(
            " ", Item.name, Item.brand, Item.size_label, Item.notes, Category.name, colour
        )
        for word in words[:8]:
            escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(searchable.ilike(f"%{escaped}%", escape="\\"))
    if f.groups:
        query = query.where(Category.group_id.in_(f.groups))
    if f.categories:
        query = query.where(Item.category_id.in_(f.categories))
    if f.slots:
        query = query.where(Item.slot.in_(f.slots))
    if f.colors:
        query = query.where(
            or_(Item.color_primary.in_(f.colors), Item.color_secondary.in_(f.colors))
        )
    if f.seasons:
        # No seasons means every season.
        query = query.where(
            or_(Item.seasons.overlap(f.seasons), func.cardinality(Item.seasons) == 0)
        )
    if f.occasions:
        query = query.where(Item.occasion_ids.overlap(f.occasions))
    if f.styles:
        query = query.where(Item.style_tags.overlap(f.styles))
    if f.statuses:
        query = query.where(Item.status.in_(f.statuses))
    return query


def _encode(sort: Sort, item: Item, position: int | None) -> str:
    values: list[Any] = [item.created_at.isoformat(), str(item.id)]
    if sort == "category":
        values.insert(0, position)
    raw = json.dumps([sort, *values]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(cursor: str, sort: Sort) -> list[Any]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        values = json.loads(raw)
        if not isinstance(values, list) or values[0] != sort:
            raise BadCursor
        values = values[1:]
        if sort == "category":
            values[0] = int(values[0])
        values[-2] = datetime.fromisoformat(values[-2])
        values[-1] = uuid.UUID(values[-1])
        return values
    except (ValueError, TypeError, IndexError, binascii.Error, json.JSONDecodeError) as error:
        raise BadCursor from error


def _after(sort: Sort, values: list[Any]) -> Any:
    """Rows that come after the cursor in the chosen order (keyset pagination)."""
    if sort == "oldest":
        created, item_id = values
        return or_(Item.created_at > created, and_(Item.created_at == created, Item.id > item_id))
    if sort == "category":
        position, created, item_id = values
        later_in_category = or_(
            Item.created_at < created, and_(Item.created_at == created, Item.id < item_id)
        )
        return or_(
            Category.position > position, and_(Category.position == position, later_in_category)
        )
    created, item_id = values
    return or_(Item.created_at < created, and_(Item.created_at == created, Item.id < item_id))


def check_fields(db: Session, user: User, fields: dict[str, Any]) -> dict[str, str]:
    """Field name -> message for every value that isn't in the reference data."""
    problems: dict[str, str] = {}

    def check(name: str, values: list[Any], allowed: set[str]) -> None:
        if any(value not in allowed for value in values if value is not None):
            problems[name] = UNKNOWN_CHOICE

    colors_used = [fields.get("color_primary"), fields.get("color_secondary")]
    if any(colors_used):
        colors = reference.known_ids(db, ColorFamily)
        check("color_primary", [fields.get("color_primary")], colors)
        check("color_secondary", [fields.get("color_secondary")], colors)
    for name in ("pattern", "fabric", "fit", "status"):
        if fields.get(name) is not None:
            check(name, [fields[name]], reference.known_terms(db, name))
    if fields.get("seasons"):
        check("seasons", fields["seasons"], reference.known_terms(db, "season"))
    if fields.get("occasion_ids"):
        check("occasion_ids", fields["occasion_ids"], reference.known_ids(db, Occasion))
    return problems


def usable_photo(
    db: Session, user: User, photo_id: uuid.UUID | None, problems: dict[str, str]
) -> ItemImage | None:
    if photo_id is None:
        return None
    photo = photos.find_photo(db, user, photo_id)
    if photo is None or photo.item_id is not None or photo.candidate_id is not None:
        problems["photo_id"] = "That photo isn't available. Upload it again."
        return None
    return photo


def _dissolve_if_single(db: Session, user: User, set_id: uuid.UUID) -> None:
    """A set of one isn't a set."""
    remaining = list(db.scalars(select(Item).where(Item.user_id == user.id, Item.set_id == set_id)))
    if len(remaining) == 1:
        remaining[0].set_id = None


def _changed(user: User) -> None:
    # Cached outfit scores (M5) compare this number to know they're stale.
    user.wardrobe_version += 1
