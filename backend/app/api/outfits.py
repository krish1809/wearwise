"""Saved outfits, and checking a set of pieces against the outfit templates."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import ApiError, error_responses
from app.api.fields import ShortText
from app.api.item_views import ItemBrief, Names, briefs, slot_order
from app.engine.outfits import Piece, check_outfit
from app.models import Outfit, OutfitItem, User
from app.services import outfits, wear

router = APIRouter(prefix="/outfits", tags=["outfits"])

PieceIds = Annotated[list[uuid.UUID], Field(max_length=outfits.MAX_PIECES)]


class OutfitPiece(BaseModel):
    slot: str
    # The item, or null once it has been deleted.
    item: ItemBrief | None
    # The item's name now, or the name it had when it was deleted.
    name: str
    removed: bool


class ReasonOut(BaseModel):
    code: str
    kind: Literal["positive", "caution"]
    text: str


class OutfitOut(BaseModel):
    id: uuid.UUID
    name: str | None
    # The name, or its first two pieces ("Navy shirt with olive chinos") when there is none.
    display_name: str
    template_id: str | None
    occasion_id: str | None
    is_favorite: bool
    # False once a piece has been deleted, until another is swapped in.
    complete: bool
    # In slot order: top, bottom, one-piece, layer, footwear, then accessories.
    pieces: list[OutfitPiece]
    wear_count: int
    last_worn_on: date | None
    # "manual" from the studio, "engine" when saved from a suggestion, which keeps the
    # engine version, score, and reasons it was shown with.
    source: Literal["manual", "engine"]
    engine_version: str | None
    score: float | None
    reasons: list[ReasonOut]
    created_at: datetime
    updated_at: datetime


class OutfitPage(BaseModel):
    outfits: list[OutfitOut]
    next_cursor: str | None


class OutfitCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_ids: PieceIds
    name: ShortText = None
    occasion_id: str | None = None
    is_favorite: bool | None = None


class OutfitUpdate(BaseModel):
    """Only the fields sent change. Sending item_ids replaces the pieces: that is how one piece
    is swapped for another."""

    model_config = ConfigDict(extra="forbid")

    item_ids: PieceIds | None = None
    name: ShortText = None
    occasion_id: str | None = None
    is_favorite: bool | None = None


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_ids: PieceIds


class OutfitCheck(BaseModel):
    complete: bool
    # The template the pieces come closest to, such as "Top and bottom".
    template_id: str | None
    template_name: str | None
    # Required slots still empty, as ids and as names.
    missing: list[str]
    missing_names: list[str]
    # Chosen items the template has no place for.
    misplaced_item_ids: list[uuid.UUID]
    # Slots holding more than one item.
    crowded: list[str]
    # Slots the template may add: a layer, accessories, fragrance.
    optional_slots: list[str]
    # What to do next, in one sentence; null when complete.
    message: str | None


def views(db: Session, user: User, found: list[Outfit]) -> list[OutfitOut]:
    """Outfits as the API shows them, built with a handful of queries for the whole list."""
    ids = [outfit.id for outfit in found]
    pieces = outfits.pieces_of(db, ids)
    names = Names(db, user)
    cards = briefs(db, names, [p.item_id for rows in pieces.values() for p in rows if p.item_id])
    order = slot_order(db)
    templates = outfits.templates(db)
    worn = wear.outfit_wear(db, ids)
    result = []
    for outfit in found:
        rows = sorted(pieces[outfit.id], key=lambda p: order.get(p.slot, 99))
        shown = [_piece(row, cards) for row in rows]
        present = [p for p in shown if p.item is not None]
        check = check_outfit(
            [
                Piece(key=str(p.item.id), slot=p.item.slot, category_id=p.item.category_id)
                for p in present
                if p.item
            ],
            templates,
        )
        stats = worn.get(outfit.id)
        result.append(
            OutfitOut(
                id=outfit.id,
                name=outfit.name,
                display_name=outfit.name or _derived_name(shown),
                template_id=outfit.template_id,
                occasion_id=outfit.occasion_id,
                is_favorite=outfit.is_favorite,
                complete=check.complete and len(present) == len(shown),
                pieces=shown,
                wear_count=stats.count if stats else 0,
                last_worn_on=stats.last_worn_on if stats else None,
                source="engine" if outfit.source == "engine" else "manual",
                engine_version=outfit.engine_version,
                score=outfit.score,
                reasons=[ReasonOut.model_validate(reason) for reason in outfit.reasons],
                created_at=outfit.created_at,
                updated_at=outfit.updated_at,
            )
        )
    return result


def _piece(row: OutfitItem, cards: dict[uuid.UUID, ItemBrief]) -> OutfitPiece:
    card = cards.get(row.item_id) if row.item_id else None
    return OutfitPiece(
        slot=row.slot,
        item=card,
        name=card.display_name if card else row.item_name,
        removed=card is None,
    )


def _derived_name(pieces: list[OutfitPiece]) -> str:
    if not pieces:
        return "Outfit"
    first = pieces[0].name
    if len(pieces) == 1:
        return first
    second = pieces[1].name
    return f"{first} with {second[:1].lower()}{second[1:]}"


def _view(db: Session, user: User, outfit: Outfit) -> OutfitOut:
    return views(db, user, [outfit])[0]


def _owned(db: Session, user: User, outfit_id: uuid.UUID) -> Outfit:
    outfit = outfits.find_outfit(db, user, outfit_id)
    if outfit is None:
        raise ApiError(404, "outfit_not_found", "That outfit doesn't exist.")
    return outfit


def _invalid(error: outfits.OutfitInvalid) -> ApiError:
    return ApiError(422, error.code, error.message, fields=error.fields)


@router.get("", response_model=OutfitPage, responses=error_responses(401, 422))
def list_outfits(
    user: CurrentUser,
    db: SessionDep,
    favorite: bool = False,
    occasion: str | None = None,
    item_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=60)] = 24,
    cursor: str | None = None,
) -> OutfitPage:
    """Saved outfits, newest first. `item_id` finds the outfits an item is part of."""
    try:
        page = outfits.list_outfits(
            db,
            user,
            favorites=favorite,
            occasion_id=occasion,
            item_id=item_id,
            limit=limit,
            cursor=cursor,
        )
    except outfits.BadCursor as error:
        raise ApiError(
            422, "bad_cursor", "That page link has expired. Start from the top."
        ) from error
    return OutfitPage(outfits=views(db, user, page.outfits), next_cursor=page.next_cursor)


@router.post("/check", response_model=OutfitCheck, responses=error_responses(401, 403, 422))
def check(body: CheckRequest, user: CurrentUser, db: SessionDep) -> OutfitCheck:
    """Which template these items fill, and what's still needed. Changes nothing."""
    items = outfits.owned_items(db, user, body.item_ids)
    if len(items) != len(set(body.item_ids)):
        message = "Some of those items don't exist."
        raise ApiError(422, "invalid_input", message, fields={"item_ids": message})
    assessment = outfits.assess(db, user, items)
    result = assessment.check
    return OutfitCheck(
        complete=result.complete,
        template_id=result.template_id,
        template_name=assessment.template_name,
        missing=list(result.missing),
        missing_names=assessment.missing_names,
        misplaced_item_ids=[uuid.UUID(piece.key) for piece in result.misplaced],
        crowded=list(result.crowded),
        optional_slots=assessment.optional_slots,
        message=assessment.message,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OutfitOut,
    responses=error_responses(401, 403, 422),
)
def create_outfit(body: OutfitCreate, user: CurrentUser, db: SessionDep) -> OutfitOut:
    """Save an outfit. It must fill a template: a top, a bottom, and footwear, for example."""
    fields = body.model_dump()
    if fields["is_favorite"] is None:
        fields["is_favorite"] = False
    try:
        outfit = outfits.create_outfit(db, user, fields)
    except outfits.OutfitInvalid as error:
        raise _invalid(error) from error
    db.commit()
    return _view(db, user, outfit)


@router.get("/{outfit_id}", response_model=OutfitOut, responses=error_responses(401, 404))
def get_outfit(outfit_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> OutfitOut:
    return _view(db, user, _owned(db, user, outfit_id))


@router.patch(
    "/{outfit_id}", response_model=OutfitOut, responses=error_responses(401, 403, 404, 422)
)
def update_outfit(
    outfit_id: uuid.UUID, body: OutfitUpdate, user: CurrentUser, db: SessionDep
) -> OutfitOut:
    outfit = _owned(db, user, outfit_id)
    try:
        outfits.update_outfit(db, user, outfit, body.model_dump(exclude_unset=True))
    except outfits.OutfitInvalid as error:
        raise _invalid(error) from error
    db.commit()
    return _view(db, user, outfit)


@router.post(
    "/{outfit_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    response_model=OutfitOut,
    responses=error_responses(401, 403, 404),
)
def duplicate_outfit(outfit_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> OutfitOut:
    """A copy to vary, saved straight away."""
    copy = outfits.duplicate(db, user, _owned(db, user, outfit_id))
    db.commit()
    return _view(db, user, copy)


@router.delete(
    "/{outfit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404),
)
def delete_outfit(outfit_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> None:
    """Delete the outfit. What was worn stays in the wear log."""
    outfits.delete_outfit(db, _owned(db, user, outfit_id))
    db.commit()
