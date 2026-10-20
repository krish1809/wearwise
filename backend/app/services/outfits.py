"""Saved outfits: one item per slot, filling a template from seed/taxonomy.json.

Each piece keeps the item's name, so when an item is deleted the outfit shows it as removed
instead of breaking. An outfit must be complete to be saved; it can become incomplete later
only by an item being deleted, and swapping in another piece completes it again.
"""

import base64
import binascii
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.engine.outfits import Check, Piece, Template, check_outfit
from app.models import (
    Item,
    Occasion,
    Outfit,
    OutfitItem,
    OutfitTemplate,
    User,
    VocabularyTerm,
)
from app.services import reference
from app.services.item_names import ItemNames

# A full outfit with every accessory is about fourteen pieces.
MAX_PIECES = 20


class OutfitInvalid(Exception):
    def __init__(
        self,
        fields: dict[str, str],
        message: str = "Check the highlighted fields.",
        code: str = "invalid_input",
    ) -> None:
        super().__init__(message)
        self.fields = fields
        self.message = message
        self.code = code


class BadCursor(Exception):
    pass


@dataclass(frozen=True)
class Assessment:
    """A check of some pieces, in words the person can act on."""

    check: Check
    template_name: str | None
    # One sentence saying what's missing or wrong; None when the outfit is complete.
    message: str | None
    missing_names: list[str]
    # Slots the template may add, in slot order.
    optional_slots: list[str]


@dataclass
class Page:
    outfits: list[Outfit]
    next_cursor: str | None


def templates(db: Session) -> list[Template]:
    rows = db.scalars(select(OutfitTemplate).order_by(OutfitTemplate.position))
    return [Template.from_seed(t.id, t.required, t.optional) for t in rows]


def owned_items(db: Session, user: User, item_ids: list[uuid.UUID]) -> list[Item]:
    query = select(Item).where(Item.user_id == user.id, Item.id.in_(set(item_ids)))
    return list(db.scalars(query))


def assess(db: Session, user: User, items: list[Item]) -> Assessment:
    """Which template the items fill, and what's still needed."""
    check = check_outfit(
        [Piece(key=str(item.id), slot=item.slot, category_id=item.category_id) for item in items],
        templates(db),
    )
    slot_names = {
        term.id: term.name
        for term in db.scalars(select(VocabularyTerm).where(VocabularyTerm.kind == "slot"))
    }
    template_name = None
    optional: list[str] = []
    if check.template_id:
        template = db.get_one(OutfitTemplate, check.template_id)
        template_name = template.name
        positions = {
            term.id: term.position
            for term in db.scalars(select(VocabularyTerm).where(VocabularyTerm.kind == "slot"))
        }
        optional = sorted(template.optional, key=lambda slot: positions.get(slot, 99))
    names = ItemNames(db, user)
    by_key = {str(item.id): item for item in items}
    missing_names = [slot_names.get(slot, slot) for slot in check.missing]

    message = None
    if check.crowded:
        crowded = ", ".join(slot_names.get(slot, slot).lower() for slot in check.crowded)
        message = f"Choose one item per slot: there's more than one {crowded}."
    elif check.misplaced:
        piece = by_key[check.misplaced[0].key]
        kind = (template_name or "this").lower()
        message = f"{names.display_name(piece)} doesn't go in a {kind} outfit."
    elif check.missing:
        message = f"Still needed: {', '.join(name.lower() for name in missing_names)}."
    return Assessment(
        check=check,
        template_name=template_name,
        message=message,
        missing_names=missing_names,
        optional_slots=optional,
    )


def create_outfit(db: Session, user: User, fields: dict[str, Any]) -> Outfit:
    item_ids = fields.pop("item_ids")
    items, check = _complete_pieces(db, user, item_ids, fields)
    outfit = Outfit(user_id=user.id, template_id=check.template_id, **fields)
    db.add(outfit)
    db.flush()
    _write_pieces(db, user, outfit, items)
    return outfit


def update_outfit(db: Session, user: User, outfit: Outfit, changes: dict[str, Any]) -> None:
    """Change the name, occasion, or favourite mark; with item_ids, replace the pieces (which
    is how one piece is swapped)."""
    changes = dict(changes)
    item_ids = changes.pop("item_ids", None)
    if changes.get("is_favorite") is None:
        changes.pop("is_favorite", None)
    if item_ids is not None:
        items, check = _complete_pieces(db, user, item_ids, changes)
        before = {piece.item_id for piece in pieces_of(db, [outfit.id])[outfit.id]}
        if before != {item.id for item in items}:
            # The engine's score and reasons were for the pieces it suggested.
            outfit.score = None
            outfit.reasons = []
        outfit.template_id = check.template_id
        db.execute(delete(OutfitItem).where(OutfitItem.outfit_id == outfit.id))
        _write_pieces(db, user, outfit, items)
    else:
        problems = _check_fields(db, changes)
        if problems:
            raise OutfitInvalid(problems)
    for name, value in changes.items():
        setattr(outfit, name, value)
    db.flush()


def duplicate(db: Session, user: User, outfit: Outfit) -> Outfit:
    """A copy to vary, pieces and all."""
    copy = Outfit(
        user_id=user.id,
        name=f"{outfit.name} (copy)"[:100] if outfit.name else None,
        template_id=outfit.template_id,
        occasion_id=outfit.occasion_id,
    )
    db.add(copy)
    db.flush()
    for piece in pieces_of(db, [outfit.id])[outfit.id]:
        db.add(
            OutfitItem(
                outfit_id=copy.id, item_id=piece.item_id, slot=piece.slot, item_name=piece.item_name
            )
        )
    db.flush()
    return copy


def delete_outfit(db: Session, outfit: Outfit) -> None:
    """Delete the outfit. Wear logs made from it keep their items."""
    db.delete(outfit)
    db.flush()


def find_outfit(db: Session, user: User, outfit_id: uuid.UUID) -> Outfit | None:
    return db.scalar(select(Outfit).where(Outfit.id == outfit_id, Outfit.user_id == user.id))


def pieces_of(db: Session, outfit_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[OutfitItem]]:
    found: dict[uuid.UUID, list[OutfitItem]] = {outfit_id: [] for outfit_id in outfit_ids}
    if outfit_ids:
        query = select(OutfitItem).where(OutfitItem.outfit_id.in_(outfit_ids))
        for piece in db.scalars(query):
            found[piece.outfit_id].append(piece)
    return found


def list_outfits(
    db: Session,
    user: User,
    *,
    favorites: bool,
    occasion_id: str | None,
    item_id: uuid.UUID | None,
    limit: int,
    cursor: str | None,
) -> Page:
    """Newest first."""
    query = select(Outfit).where(Outfit.user_id == user.id)
    if favorites:
        query = query.where(Outfit.is_favorite)
    if occasion_id:
        query = query.where(Outfit.occasion_id == occasion_id)
    if item_id is not None:
        query = query.where(
            Outfit.id.in_(select(OutfitItem.outfit_id).where(OutfitItem.item_id == item_id))
        )
    if cursor:
        created, outfit_id = _decode(cursor)
        query = query.where(
            or_(
                Outfit.created_at < created,
                and_(Outfit.created_at == created, Outfit.id < outfit_id),
            )
        )
    query = query.order_by(Outfit.created_at.desc(), Outfit.id.desc())
    rows = list(db.scalars(query.limit(limit + 1)))
    page = rows[:limit]
    next_cursor = _encode(page[-1]) if len(rows) > limit and page else None
    return Page(outfits=page, next_cursor=next_cursor)


def count_outfits(db: Session, user: User) -> int:
    return db.scalar(select(func.count()).where(Outfit.user_id == user.id)) or 0


def _complete_pieces(
    db: Session, user: User, item_ids: list[uuid.UUID], fields: dict[str, Any]
) -> tuple[list[Item], Check]:
    problems = _check_fields(db, fields)
    unique_ids = list(dict.fromkeys(item_ids))
    items = owned_items(db, user, unique_ids)
    if len(unique_ids) > MAX_PIECES:
        problems["item_ids"] = f"An outfit can have up to {MAX_PIECES} pieces."
    elif len(items) != len(unique_ids):
        problems["item_ids"] = "Some of those items don't exist."
    elif archived := [item for item in items if item.archived_at is not None]:
        name = ItemNames(db, user).display_name(archived[0])
        problems["item_ids"] = f"{name} is archived. Restore it to use it in an outfit."
    if problems:
        raise OutfitInvalid(problems)
    assessment = assess(db, user, items)
    if not assessment.check.complete:
        message = assessment.message or "This outfit isn't complete."
        raise OutfitInvalid({"item_ids": message}, message, code="outfit_incomplete")
    return items, assessment.check


def _check_fields(db: Session, fields: dict[str, Any]) -> dict[str, str]:
    problems: dict[str, str] = {}
    occasion = fields.get("occasion_id")
    if occasion is not None and occasion not in reference.known_ids(db, Occasion):
        problems["occasion_id"] = "Choose one of the options shown."
    return problems


def _write_pieces(db: Session, user: User, outfit: Outfit, items: list[Item]) -> None:
    names = ItemNames(db, user)
    for item in items:
        db.add(
            OutfitItem(
                outfit_id=outfit.id,
                item_id=item.id,
                slot=item.slot,
                item_name=names.display_name(item),
            )
        )
    db.flush()


def _encode(outfit: Outfit) -> str:
    raw = json.dumps([outfit.created_at.isoformat(), str(outfit.id)])
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        created, outfit_id = json.loads(raw)
        return datetime.fromisoformat(created), uuid.UUID(outfit_id)
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError) as error:
        raise BadCursor from error
