"""Trips and their packing lists."""

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep, WeatherDep
from app.api.errors import ApiError, error_responses
from app.api.item_views import ItemBrief, Names, briefs
from app.api.outfits import ReasonOut
from app.api.plan import PlanPiece, WeatherOut
from app.models import Trip, User
from app.services import trips

router = APIRouter(prefix="/trips", tags=["trips"])


class TripIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: Annotated[str, Field(min_length=1, max_length=100)]
    # The place chosen from the search, for the forecast; without it the trip goes by the
    # manual weather setting or the season.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    start_date: date
    end_date: date
    # The occasion for every day, and any days that differ.
    occasion_id: str
    day_occasions: dict[date, str] | None = None


class TripDayOut(BaseModel):
    day: date
    occasion_id: str
    weather: WeatherOut
    pieces: list[PlanPiece]
    reasons: list[ReasonOut]
    score: float | None
    # Why the day has no outfit, as sentences.
    missing: list[str]


class TripItemOut(BaseModel):
    item: ItemBrief
    packed: bool


class Basics(BaseModel):
    """Counted basics to pack alongside, one a day: a plain checklist."""

    socks: int
    innerwear: int


class TripOut(BaseModel):
    id: uuid.UUID
    destination: str
    start_date: date
    end_date: date
    days: list[TripDayOut]
    # The packing list, in slot order. Packed items are marked "Packed" in the wardrobe.
    items: list[TripItemOut]
    basics: Basics
    engine_version: str | None
    created_at: datetime


class TripSummary(BaseModel):
    id: uuid.UUID
    destination: str
    start_date: date
    end_date: date
    item_count: int


class PackedIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=200)]
    packed: bool


def _view(db: Session, user: User, trip: Trip) -> TripOut:
    on_list = trips.items_of(db, trip)
    names = Names(db, user)
    day_ids = [uuid.UUID(item_id) for day in trip.outfits for item_id in day["item_ids"]]
    cards = briefs(db, names, [*on_list, *day_ids])
    occasions = {day["day"]: day["occasion_id"] for day in trip.days}
    days = []
    for day in trip.outfits:
        core = set(day["core_ids"])
        ids = [uuid.UUID(item_id) for item_id in day["item_ids"]]
        days.append(
            TripDayOut(
                day=date.fromisoformat(day["day"]),
                occasion_id=occasions[day["day"]],
                weather=WeatherOut.model_validate(day["weather"]),
                pieces=[
                    PlanPiece(slot=cards[i].slot, item=cards[i], core=str(i) in core)
                    for i in ids
                    if i in cards
                ],
                reasons=[ReasonOut.model_validate(reason) for reason in day["reasons"]],
                score=day["score"],
                missing=day["missing"],
            )
        )
    order = {item_id: index for index, item_id in enumerate(on_list)}
    count = len(trip.days)
    return TripOut(
        id=trip.id,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        days=days,
        items=[
            TripItemOut(item=cards[item_id], packed=cards[item_id].status == "packed")
            for item_id in sorted(on_list, key=lambda item_id: order[item_id])
            if item_id in cards
        ],
        basics=Basics(socks=count, innerwear=count),
        engine_version=trip.engine_version,
        created_at=trip.created_at,
    )


def _owned(db: Session, user: User, trip_id: uuid.UUID) -> Trip:
    trip = trips.find(db, user, trip_id)
    if trip is None:
        raise ApiError(404, "trip_not_found", "That trip doesn't exist.")
    return trip


def _invalid(error: trips.TripInvalid) -> ApiError:
    return ApiError(422, "invalid_input", "Check the highlighted fields.", fields=error.fields)


@router.get("", response_model=list[TripSummary], responses=error_responses(401))
def list_trips(user: CurrentUser, db: SessionDep) -> list[TripSummary]:
    """Trips, latest first."""
    return [
        TripSummary(
            id=trip.id,
            destination=trip.destination,
            start_date=trip.start_date,
            end_date=trip.end_date,
            item_count=len(trips.items_of(db, trip)),
        )
        for trip in trips.listed(db, user)
    ]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TripOut,
    responses=error_responses(401, 403, 422),
)
def create_trip(body: TripIn, user: CurrentUser, db: SessionDep, provider: WeatherDep) -> TripOut:
    """Plan a trip: a compact packing list and an outfit for each day."""
    fields = body.model_dump()
    if (fields["latitude"] is None) != (fields["longitude"] is None):
        raise ApiError(
            422,
            "invalid_input",
            "Check the highlighted fields.",
            fields={"destination": "Choose the place from the search results."},
        )
    try:
        trip = trips.create(db, user, provider, fields)
    except trips.TripInvalid as error:
        raise _invalid(error) from error
    db.commit()
    return _view(db, user, trip)


@router.get("/{trip_id}", response_model=TripOut, responses=error_responses(401, 404))
def get_trip(trip_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> TripOut:
    return _view(db, user, _owned(db, user, trip_id))


@router.post("/{trip_id}/replan", response_model=TripOut, responses=error_responses(401, 403, 404))
def replan_trip(
    trip_id: uuid.UUID, user: CurrentUser, db: SessionDep, provider: WeatherDep
) -> TripOut:
    """Plan the packing again from the wardrobe as it is now."""
    trip = _owned(db, user, trip_id)
    trips.replan(db, user, provider, trip)
    db.commit()
    return _view(db, user, trip)


@router.post(
    "/{trip_id}/packed", response_model=TripOut, responses=error_responses(401, 403, 404, 422)
)
def mark_packed(trip_id: uuid.UUID, body: PackedIn, user: CurrentUser, db: SessionDep) -> TripOut:
    """Mark items as packed (they leave everyday suggestions) or unpacked."""
    trip = _owned(db, user, trip_id)
    try:
        trips.set_packed(db, user, trip, body.item_ids, body.packed)
    except trips.TripInvalid as error:
        raise _invalid(error) from error
    db.commit()
    return _view(db, user, trip)


@router.delete(
    "/{trip_id}", status_code=status.HTTP_204_NO_CONTENT, responses=error_responses(401, 403, 404)
)
def delete_trip(trip_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> None:
    """Delete the trip. Anything still marked packed for it is unpacked."""
    trips.remove(db, user, _owned(db, user, trip_id))
    db.commit()
