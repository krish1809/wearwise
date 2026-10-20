"""My Week: the plan for seven days, events, and the laundry."""

import uuid
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep, WeatherDep
from app.api.errors import ApiError, error_responses
from app.api.fields import NoteText, ShortText
from app.api.item_views import ItemBrief, Names, briefs
from app.api.outfits import ReasonOut
from app.engine.config import ENGINE_VERSION
from app.engine.types import ScoredOutfit
from app.models import Event, Occasion, User
from app.services import events as event_service
from app.services import laundry, planning, rate_limit, reference, wear
from app.services import profile as profiles

router = APIRouter(tags=["my week"])

PLANS_PER_USER = rate_limit.Limit(attempts=60, window=timedelta(hours=1))
# A day's plan starts from today; the browser may be up to a day ahead of the server (UTC).
SLACK = timedelta(days=1)


class WeatherOut(BaseModel):
    # forecast (Open-Meteo), manual (the person's setting), or season (nothing else known).
    source: Literal["forecast", "manual", "season"]
    feels_like: float | None
    rain_chance: int | None


class EventOut(BaseModel):
    id: uuid.UUID
    day: date
    title: str
    occasion_id: str
    note: str | None


class PlanPiece(BaseModel):
    slot: str
    item: ItemBrief
    core: bool


class PlanDayOut(BaseModel):
    day: date
    # The occasion in force, and where it comes from: chosen for the day, an event, the
    # usual one for the weekday, or none yet.
    occasion_id: str | None
    occasion_source: Literal["chosen", "event", "usual", "none"]
    events: list[EventOut]
    weather: WeatherOut
    # The outfit, in slot order; empty when nothing is planned.
    pieces: list[PlanPiece]
    reasons: list[ReasonOut]
    score: float | None
    # Why nothing could be planned, as sentences.
    missing: list[str]
    locked: bool
    worn: bool
    # Planned for an occasion the day no longer has: plan the week again.
    outdated: bool
    # A piece has been deleted or archived since.
    stale: bool
    # Pieces not available right now (in the laundry, lent...), by name.
    unavailable: list[str]


class WeekOut(BaseModel):
    start: date
    days: list[PlanDayOut]
    laundry_weekday: int | None
    engine_version: str


class GenerateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The first of the seven days; today when left out.
    start: date | None = None


class DayChange(BaseModel):
    """Only the fields sent change. occasion_id null goes back to the usual occasion;
    item_ids swaps in another outfit (from the day's options) and locks the day."""

    model_config = ConfigDict(extra="forbid")

    locked: bool | None = None
    occasion_id: str | None = None
    item_ids: list[uuid.UUID] | None = Field(default=None, max_length=20)


class OptionOut(BaseModel):
    item_ids: list[uuid.UUID]
    pieces: list[PlanPiece]
    reasons: list[ReasonOut]
    score: float


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date
    title: Annotated[str, Field(min_length=1, max_length=100)]
    occasion_id: str
    note: NoteText = None


class EventChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date | None = None
    title: ShortText = None
    occasion_id: str | None = None
    note: NoteText = None


class LaundryItem(BaseModel):
    item: ItemBrief
    in_laundry: bool
    wears_since_wash: int
    wears_before_wash: int | None


class LaundryOut(BaseModel):
    items: list[LaundryItem]


class LaundryDone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=500)]


def _event(event: Event) -> EventOut:
    return EventOut(
        id=event.id,
        day=event.day,
        title=event.title,
        occasion_id=event.occasion_id,
        note=event.note,
    )


def _views(db: Session, user: User, days: list[planning.Day]) -> list[PlanDayOut]:
    names = Names(db, user)
    ids = [item_id for entry in days if entry.row for item_id in entry.row.item_ids]
    cards = briefs(db, names, ids)
    found = []
    for entry in days:
        row = entry.row
        item_ids = list(row.item_ids) if row else []
        core = set(row.core_ids) if row else set()
        present = [cards[item_id] for item_id in item_ids if item_id in cards]
        found.append(
            PlanDayOut(
                day=entry.day,
                occasion_id=entry.occasion_id,
                occasion_source=entry.occasion_source,
                events=[_event(event) for event in entry.events],
                weather=WeatherOut(
                    source=entry.weather.source,
                    feels_like=entry.weather.feels_like,
                    rain_chance=entry.weather.rain_chance,
                ),
                pieces=[PlanPiece(slot=c.slot, item=c, core=c.id in core) for c in present],
                reasons=[ReasonOut.model_validate(reason) for reason in row.reasons] if row else [],
                score=row.score if row else None,
                missing=[str(missing["text"]) for missing in row.missing] if row else [],
                locked=bool(row and row.locked),
                worn=bool(row and row.wear_log_id),
                outdated=entry.outdated,
                stale=len(present) != len(item_ids) or any(card.archived for card in present),
                unavailable=[card.display_name for card in present if card.status != "available"],
            )
        )
    return found


def _week(
    db: Session, user: User, start: date, days: list[planning.Day], weekday: int | None
) -> WeekOut:
    return WeekOut(
        start=start,
        days=_views(db, user, days),
        laundry_weekday=weekday,
        engine_version=ENGINE_VERSION,
    )


def _from_today(start: date) -> None:
    if start < wear.today() - SLACK:
        raise ApiError(
            422,
            "invalid_input",
            "Plan from today onwards.",
            fields={"start": "Plan from today onwards."},
        )


def _invalid(error: planning.PlanInvalid) -> ApiError:
    return ApiError(422, "invalid_input", error.message, fields=error.fields)


@router.get("/plan", response_model=WeekOut, responses=error_responses(401, 422))
def get_week(
    user: CurrentUser, db: SessionDep, provider: WeatherDep, start: date | None = None
) -> WeekOut:
    """Seven days from start (today by default): occasion, weather, and the planned outfit."""
    first = start or wear.today()
    profile, days = planning.week(db, user, provider, first)
    db.commit()
    return _week(db, user, first, days, profile.laundry_weekday)


@router.post(
    "/plan/generate", response_model=WeekOut, responses=error_responses(401, 403, 422, 429)
)
def generate(body: GenerateIn, user: CurrentUser, db: SessionDep, provider: WeatherDep) -> WeekOut:
    """Plan the seven days from start. Locked days and days already worn stay as they are."""
    first = body.start or wear.today()
    _from_today(first)
    try:
        rate_limit.hit(db, f"plan:user:{user.id}", PLANS_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(
            429, "rate_limited", "That's a lot of planning in an hour. Try again a little later."
        ) from error
    days = planning.generate(db, user, provider, first)
    weekday = profiles.get_or_create_profile(db, user).laundry_weekday
    db.commit()
    return _week(db, user, first, days, weekday)


@router.patch(
    "/plan/days/{day}", response_model=PlanDayOut, responses=error_responses(401, 403, 422)
)
def change_day(
    day: date,
    body: DayChange,
    user: CurrentUser,
    db: SessionDep,
    provider: WeatherDep,
    start: date | None = None,
) -> PlanDayOut:
    """Lock or unlock the day, choose its occasion, or swap in one of its options."""
    first = start or wear.today()
    if not first <= day < first + timedelta(days=planning.WEEK):
        raise ApiError(
            422,
            "invalid_input",
            "That day isn't in this week.",
            fields={"day": "That day isn't in this week."},
        )
    changes = body.model_dump(exclude_unset=True)
    occasion = changes.get("occasion_id")
    if occasion is not None and occasion not in reference.known_ids(db, Occasion):
        raise ApiError(
            422,
            "invalid_input",
            "Check the highlighted fields.",
            fields={"occasion_id": "Choose one of the options shown."},
        )
    try:
        entry = planning.change(db, user, provider, first, day, changes)
    except planning.PlanInvalid as error:
        raise _invalid(error) from error
    db.commit()
    return _views(db, user, [entry])[0]


@router.get(
    "/plan/days/{day}/options", response_model=list[OptionOut], responses=error_responses(401, 422)
)
def day_options(
    day: date,
    user: CurrentUser,
    db: SessionDep,
    provider: WeatherDep,
    start: date | None = None,
) -> list[OptionOut]:
    """Other outfits for the day that keep the rest of the week within the rules."""
    first = start or wear.today()
    try:
        found = planning.options(db, user, provider, first, day)
    except planning.PlanInvalid as error:
        raise _invalid(error) from error
    db.commit()
    return _options(db, user, found)


def _options(db: Session, user: User, found: list[ScoredOutfit]) -> list[OptionOut]:
    names = Names(db, user)
    cards = briefs(db, names, [uuid.UUID(item.id) for outfit in found for item in outfit.items])
    result = []
    for outfit in found:
        core = set(outfit.core_ids)
        result.append(
            OptionOut(
                item_ids=[uuid.UUID(item.id) for item in outfit.items],
                pieces=[
                    PlanPiece(slot=item.slot, item=cards[uuid.UUID(item.id)], core=item.id in core)
                    for item in outfit.items
                    if uuid.UUID(item.id) in cards
                ],
                reasons=[
                    ReasonOut(code=reason.code, kind=reason.kind, text=reason.text)
                    for reason in outfit.reasons
                ],
                score=outfit.score,
            )
        )
    return result


@router.post(
    "/plan/days/{day}/wear",
    response_model=PlanDayOut,
    responses=error_responses(401, 403, 422),
)
def wear_day(day: date, user: CurrentUser, db: SessionDep, provider: WeatherDep) -> PlanDayOut:
    """Log the day's outfit in the wear log. Logging it again changes nothing."""
    try:
        entry = planning.wear_day(db, user, provider, day)
    except planning.PlanInvalid as error:
        raise _invalid(error) from error
    except wear.WearInvalid as error:
        raise ApiError(
            422, "invalid_input", "Check the highlighted fields.", fields=error.fields
        ) from error
    db.commit()
    return _views(db, user, [entry])[0]


@router.get("/events", response_model=list[EventOut], responses=error_responses(401, 422))
def list_events(
    user: CurrentUser,
    db: SessionDep,
    start: date | None = None,
    days: Annotated[int, Query(ge=1, le=366)] = 90,
) -> list[EventOut]:
    """Events from start (today by default) for the given number of days."""
    first = start or wear.today()
    found = event_service.between(db, user, first, first + timedelta(days=days - 1))
    return [_event(event) for event in found]


@router.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    response_model=EventOut,
    responses=error_responses(401, 403, 422),
)
def create_event(body: EventIn, user: CurrentUser, db: SessionDep) -> EventOut:
    try:
        event = event_service.create(db, user, body.model_dump())
    except event_service.EventInvalid as error:
        raise ApiError(
            422, "invalid_input", "Check the highlighted fields.", fields=error.fields
        ) from error
    db.commit()
    return _event(event)


def _owned_event(db: Session, user: User, event_id: uuid.UUID) -> Event:
    event = event_service.find(db, user, event_id)
    if event is None:
        raise ApiError(404, "event_not_found", "That event doesn't exist.")
    return event


@router.patch(
    "/events/{event_id}", response_model=EventOut, responses=error_responses(401, 403, 404, 422)
)
def update_event(
    event_id: uuid.UUID, body: EventChange, user: CurrentUser, db: SessionDep
) -> EventOut:
    event = _owned_event(db, user, event_id)
    changes = {key: value for key, value in body.model_dump(exclude_unset=True).items()}
    for required in ("day", "title", "occasion_id"):
        if required in changes and changes[required] is None:
            raise ApiError(
                422,
                "invalid_input",
                "Check the highlighted fields.",
                fields={required: "This can't be empty."},
            )
    try:
        event_service.update(db, event, changes)
    except event_service.EventInvalid as error:
        raise ApiError(
            422, "invalid_input", "Check the highlighted fields.", fields=error.fields
        ) from error
    db.commit()
    return _event(event)


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404),
)
def delete_event(event_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> None:
    event_service.delete(db, _owned_event(db, user, event_id))
    db.commit()


def _laundry(db: Session, user: User) -> LaundryOut:
    rows = laundry.pending(db, user)
    cards = briefs(db, Names(db, user), [row.id for row in rows])
    return LaundryOut(
        items=[
            LaundryItem(
                item=cards[row.id],
                in_laundry=row.status == "laundry",
                wears_since_wash=row.wears_since_wash,
                wears_before_wash=row.wears_before_wash,
            )
            for row in rows
        ]
    )


@router.get("/laundry", response_model=LaundryOut, responses=error_responses(401))
def get_laundry(user: CurrentUser, db: SessionDep) -> LaundryOut:
    """What's in the laundry, and what's been worn as often as it goes between washes."""
    return _laundry(db, user)


@router.post("/laundry/done", response_model=LaundryOut, responses=error_responses(401, 403, 422))
def laundry_done(body: LaundryDone, user: CurrentUser, db: SessionDep) -> LaundryOut:
    """These are clean: back to available, with their wear counts starting again."""
    try:
        laundry.done(db, user, body.item_ids)
    except laundry.LaundryInvalid as error:
        raise ApiError(
            422, "invalid_input", "Check the highlighted fields.", fields=error.fields
        ) from error
    db.commit()
    return _laundry(db, user)
