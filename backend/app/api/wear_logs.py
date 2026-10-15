"""The wear log: what was worn, on which day."""

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import ApiError, error_responses
from app.api.fields import NoteText
from app.api.item_views import ItemBrief, Names, briefs, slot_order
from app.api.outfits import views as outfit_views
from app.models import Outfit, User, WearLog
from app.services import outfits, wear

router = APIRouter(prefix="/wear-logs", tags=["wear log"])

ItemIds = Annotated[list[uuid.UUID], Field(max_length=outfits.MAX_PIECES)]


class WornPiece(BaseModel):
    slot: str
    # The item, or null once it has been deleted.
    item: ItemBrief | None
    name: str
    removed: bool


class WearLogOut(BaseModel):
    id: uuid.UUID
    worn_on: date
    # The outfit it was logged from, if it still exists.
    outfit_id: uuid.UUID | None
    outfit_name: str | None
    occasion_id: str | None
    note: str | None
    # What was worn, as it was logged, in slot order.
    pieces: list[WornPiece]
    created_at: datetime


class WearLogPage(BaseModel):
    logs: list[WearLogOut]
    next_cursor: str | None


class WearLogCreate(BaseModel):
    """An outfit, or loose items, worn on a day. Logging an outfit copies its pieces."""

    model_config = ConfigDict(extra="forbid")

    worn_on: date
    outfit_id: uuid.UUID | None = None
    item_ids: ItemIds | None = None
    occasion_id: str | None = None
    note: NoteText = None


class WearLogUpdate(BaseModel):
    """Only the fields sent change. item_ids replaces what was worn."""

    model_config = ConfigDict(extra="forbid")

    worn_on: date | None = None
    item_ids: ItemIds | None = None
    occasion_id: str | None = None
    note: NoteText = None


def views(db: Session, user: User, logs: list[WearLog]) -> list[WearLogOut]:
    pieces = wear.pieces_of(db, [log.id for log in logs])
    names = Names(db, user)
    cards = briefs(db, names, [p.item_id for rows in pieces.values() for p in rows if p.item_id])
    order = slot_order(db)
    outfit_ids = {log.outfit_id for log in logs if log.outfit_id}
    found = list(
        db.scalars(select(Outfit).where(Outfit.id.in_(outfit_ids), Outfit.user_id == user.id))
    )
    outfit_names = {view.id: view.display_name for view in outfit_views(db, user, found)}
    result = []
    for log in logs:
        worn = []
        for row in sorted(pieces[log.id], key=lambda p: order.get(p.slot, 99)):
            card = cards.get(row.item_id) if row.item_id else None
            worn.append(
                WornPiece(
                    slot=row.slot,
                    item=card,
                    name=card.display_name if card else row.item_name,
                    removed=card is None,
                )
            )
        result.append(
            WearLogOut(
                id=log.id,
                worn_on=log.worn_on,
                outfit_id=log.outfit_id,
                outfit_name=outfit_names.get(log.outfit_id) if log.outfit_id else None,
                occasion_id=log.occasion_id,
                note=log.note,
                pieces=worn,
                created_at=log.created_at,
            )
        )
    return result


def _owned(db: Session, user: User, log_id: uuid.UUID) -> WearLog:
    log = wear.find_log(db, user, log_id)
    if log is None:
        raise ApiError(404, "wear_log_not_found", "That wear log doesn't exist.")
    return log


def _invalid(error: wear.WearInvalid) -> ApiError:
    return ApiError(422, "invalid_input", "Check the highlighted fields.", fields=error.fields)


@router.get("", response_model=WearLogPage, responses=error_responses(401, 422))
def list_logs(
    user: CurrentUser,
    db: SessionDep,
    item_id: uuid.UUID | None = None,
    outfit_id: uuid.UUID | None = None,
    on: date | None = None,
    limit: Annotated[int, Query(ge=1, le=60)] = 20,
    cursor: str | None = None,
) -> WearLogPage:
    """What was worn, newest day first. Filter to one item, one outfit, or one day."""
    try:
        page = wear.list_logs(
            db, user, item_id=item_id, outfit_id=outfit_id, on=on, limit=limit, cursor=cursor
        )
    except wear.BadCursor as error:
        raise ApiError(
            422, "bad_cursor", "That page link has expired. Start from the top."
        ) from error
    return WearLogPage(logs=views(db, user, page.logs), next_cursor=page.next_cursor)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=WearLogOut,
    responses={200: {"model": WearLogOut}, **error_responses(401, 403, 422)},
)
def log_wear(
    body: WearLogCreate, response: Response, user: CurrentUser, db: SessionDep
) -> WearLogOut:
    """Mark an outfit or some items as worn. The same outfit on the same day is logged once:
    a repeat answers 200 with the existing log."""
    try:
        log, created = wear.log_wear(
            db,
            user,
            worn_on=body.worn_on,
            outfit_id=body.outfit_id,
            item_ids=body.item_ids,
            occasion_id=body.occasion_id,
            note=body.note,
        )
    except wear.WearInvalid as error:
        raise _invalid(error) from error
    db.commit()
    if not created:
        response.status_code = status.HTTP_200_OK
    return views(db, user, [log])[0]


@router.patch("/{log_id}", response_model=WearLogOut, responses=error_responses(401, 403, 404, 422))
def update_log(
    log_id: uuid.UUID, body: WearLogUpdate, user: CurrentUser, db: SessionDep
) -> WearLogOut:
    log = _owned(db, user, log_id)
    try:
        wear.update_log(db, user, log, body.model_dump(exclude_unset=True))
    except wear.WearInvalid as error:
        raise _invalid(error) from error
    db.commit()
    return views(db, user, [log])[0]


@router.delete(
    "/{log_id}", status_code=status.HTTP_204_NO_CONTENT, responses=error_responses(401, 403, 404)
)
def delete_log(log_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> None:
    wear.delete_log(db, _owned(db, user, log_id))
    db.commit()
