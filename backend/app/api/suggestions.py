"""Outfit suggestions from the engine, and what the person does with them.

One action serves the three entry points: no anchors suggests for an occasion, one anchor
answers "what goes with this?", and two or more complete an outfit.
"""

import uuid
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import ApiError, error_responses
from app.api.fields import NoteText, ShortText
from app.api.item_views import ItemBrief, Names, briefs
from app.api.outfits import OutfitOut, ReasonOut
from app.api.outfits import views as outfit_views
from app.api.wear_logs import WearLogOut
from app.api.wear_logs import views as wear_views
from app.models import Suggestion, User
from app.services import outfits, rate_limit, reference, suggestions, wear

suggest_router = APIRouter(prefix="/outfits", tags=["suggestions"])
router = APIRouter(prefix="/suggestions", tags=["suggestions"])

SUGGESTIONS_PER_USER = rate_limit.Limit(attempts=300, window=timedelta(hours=1))


class SuggestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Needed unless anchors are given; with anchors it's optional.
    occasion_id: str | None = None
    # summer, monsoon, winter, or mild; the current season when left out.
    season: str | None = None
    # A style to lean towards; the profile's styles when left out.
    style_id: str | None = None
    # Pieces every suggestion must include.
    anchor_item_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    # Pieces to leave out this time.
    exclude_item_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    count: int = 10


class SuggestionPiece(BaseModel):
    slot: str
    item: ItemBrief
    # Core pieces are the required slots and the layer; the rest are finishing touches.
    core: bool


class SuggestionOut(BaseModel):
    id: uuid.UUID
    # occasion, with_item, or complete.
    kind: str
    template_id: str
    occasion_id: str | None
    season: str | None
    score: float
    # True when nothing fitted the occasion and this relaxes it by a step.
    compromise: bool
    engine_version: str
    # In slot order.
    pieces: list[SuggestionPiece]
    # The strongest positives, then any cautions, as sentences.
    reasons: list[ReasonOut]
    rating: Literal["like", "dislike", "skip"] | None
    saved_outfit_id: uuid.UUID | None
    worn_on: date | None
    # True once a piece has been deleted or archived: it can't be saved or worn any more.
    stale: bool


class MissingOut(BaseModel):
    slot: str
    slot_name: str
    code: str
    text: str


class SuggestionsOut(BaseModel):
    suggestions: list[SuggestionOut]
    # Set when nothing fits as asked: which slot is the problem, and why.
    missing: list[MissingOut]
    compromise: bool
    # A sentence when there are fewer outfits than asked for.
    note: str | None
    # The season the suggestions were made for.
    season: str
    engine_version: str


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["like", "dislike", "skip"]
    # Why a dislike: one piece, the colours, the formality, the occasion, or something else.
    reason: Literal["item", "colors", "formality", "occasion", "other"] | None = None
    # The piece, when the reason is "item".
    item_id: uuid.UUID | None = None


class SaveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortText = None
    occasion_id: str | None = None
    is_favorite: bool | None = None


class WearIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worn_on: date
    note: NoteText = None


def views(db: Session, user: User, rows: list[Suggestion]) -> list[SuggestionOut]:
    names = Names(db, user)
    cards = briefs(db, names, [item_id for row in rows for item_id in row.item_ids])
    result = []
    for row in rows:
        core = set(row.core_ids)
        present = [cards[item_id] for item_id in row.item_ids if item_id in cards]
        result.append(
            SuggestionOut(
                id=row.id,
                kind=row.kind,
                template_id=row.template_id,
                occasion_id=row.occasion_id,
                season=row.season,
                score=row.score,
                compromise=row.compromise,
                engine_version=row.engine_version,
                pieces=[
                    SuggestionPiece(slot=card.slot, item=card, core=card.id in core)
                    for card in present
                ],
                reasons=[ReasonOut.model_validate(reason) for reason in row.reasons],
                rating=row.rating if row.rating in suggestions.RATINGS else None,
                saved_outfit_id=row.saved_outfit_id,
                worn_on=row.worn_on,
                stale=len(present) != len(row.item_ids) or any(card.archived for card in present),
            )
        )
    return result


def _owned(db: Session, user: User, suggestion_id: uuid.UUID) -> Suggestion:
    found = suggestions.find(db, user, suggestion_id)
    if found is None:
        raise ApiError(404, "suggestion_not_found", "That suggestion doesn't exist.")
    return found


def _stale() -> ApiError:
    return ApiError(
        409,
        "suggestion_stale",
        "A piece of this outfit has been deleted or archived. Ask for new suggestions.",
    )


@suggest_router.post(
    "/suggest", response_model=SuggestionsOut, responses=error_responses(401, 403, 422, 429)
)
def suggest(body: SuggestRequest, user: CurrentUser, db: SessionDep) -> SuggestionsOut:
    """Ranked, varied outfits from the person's available items, each with its reasons.
    With anchor_item_ids, every outfit includes those pieces."""
    try:
        rate_limit.hit(db, f"suggest:user:{user.id}", SUGGESTIONS_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(
            429,
            "rate_limited",
            "That's a lot of suggestions in an hour. Try again a little later.",
        ) from error
    request = suggestions.Request(
        occasion_id=body.occasion_id,
        season=body.season,
        style_id=body.style_id,
        anchor_ids=body.anchor_item_ids,
        exclude_ids=body.exclude_item_ids,
        count=body.count,
    )
    try:
        result = suggestions.run(db, user, request)
    except suggestions.SuggestInvalid as error:
        raise ApiError(422, error.code, error.message, fields=error.fields) from error
    db.commit()
    slot_names = {term.id: term.name for term in reference.terms(db, "slot")}
    return SuggestionsOut(
        suggestions=views(db, user, result.rows),
        missing=[
            MissingOut(
                slot=missing.slot,
                slot_name=slot_names.get(missing.slot, missing.slot),
                code=missing.code,
                text=missing.text,
            )
            for missing in result.engine.missing
        ],
        compromise=result.engine.compromise,
        note=result.engine.note,
        season=result.season,
        engine_version=result.engine.engine_version,
    )


@router.post(
    "/{suggestion_id}/feedback",
    response_model=SuggestionOut,
    responses=error_responses(401, 403, 404, 422),
)
def rate(
    suggestion_id: uuid.UUID, body: FeedbackIn, user: CurrentUser, db: SessionDep
) -> SuggestionOut:
    """Like, dislike, or skip a suggestion. A new rating replaces the last one. Likes and
    dislikes change how future suggestions rank."""
    row = _owned(db, user, suggestion_id)
    try:
        suggestions.rate(db, user, row, body.verdict, body.reason, body.item_id)
    except suggestions.SuggestInvalid as error:
        raise ApiError(422, error.code, error.message, fields=error.fields) from error
    db.commit()
    return views(db, user, [row])[0]


@router.delete(
    "/{suggestion_id}/feedback",
    response_model=SuggestionOut,
    responses=error_responses(401, 403, 404),
)
def clear_rating(suggestion_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> SuggestionOut:
    """Take back a like, dislike, or skip."""
    row = _owned(db, user, suggestion_id)
    suggestions.clear_rating(db, row)
    db.commit()
    return views(db, user, [row])[0]


@router.post(
    "/{suggestion_id}/save",
    status_code=status.HTTP_201_CREATED,
    response_model=OutfitOut,
    responses={200: {"model": OutfitOut}, **error_responses(401, 403, 404, 409, 422)},
)
def save(
    suggestion_id: uuid.UUID, body: SaveIn, response: Response, user: CurrentUser, db: SessionDep
) -> OutfitOut:
    """Save the suggestion as an outfit. Saving it again answers 200 with the same outfit."""
    row = _owned(db, user, suggestion_id)
    already = row.saved_outfit_id is not None and outfits.find_outfit(db, user, row.saved_outfit_id)
    try:
        outfit = suggestions.save(db, user, row, body.model_dump(exclude_none=True))
    except suggestions.SuggestionStale as error:
        raise _stale() from error
    except outfits.OutfitInvalid as error:
        raise ApiError(422, error.code, error.message, fields=error.fields) from error
    db.commit()
    if already:
        response.status_code = status.HTTP_200_OK
    return outfit_views(db, user, [outfit])[0]


@router.post(
    "/{suggestion_id}/wear",
    status_code=status.HTTP_201_CREATED,
    response_model=WearLogOut,
    responses={200: {"model": WearLogOut}, **error_responses(401, 403, 404, 409, 422)},
)
def wear_it(
    suggestion_id: uuid.UUID, body: WearIn, response: Response, user: CurrentUser, db: SessionDep
) -> WearLogOut:
    """Log the suggestion as worn on a day. Logging it again answers 200 with the same entry."""
    row = _owned(db, user, suggestion_id)
    already = row.wear_log_id is not None and wear.find_log(db, user, row.wear_log_id)
    try:
        log = suggestions.wear_today(db, user, row, body.worn_on, body.note)
    except suggestions.SuggestionStale as error:
        raise _stale() from error
    except wear.WearInvalid as error:
        raise ApiError(
            422, "invalid_input", "Check the highlighted fields.", fields=error.fields
        ) from error
    db.commit()
    if already:
        response.status_code = status.HTTP_200_OK
    return wear_views(db, user, [log])[0]
