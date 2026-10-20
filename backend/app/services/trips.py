"""Trips: a destination, dates, and the occasion of each day, packed into a compact list
(app/engine/packing.py) with an outfit per day. Marking items as packed sets their status, so
they leave everyday suggestions until they're unpacked."""

import uuid
from dataclasses import replace
from datetime import date, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.adapters.weather import WeatherProvider
from app.engine.config import DEFAULT
from app.engine.generate import season_for
from app.engine.packing import TripDay, pack
from app.models import Item, Occasion, Trip, TripItem, User
from app.services import profile as profiles
from app.services import reference, suggestions
from app.services import weather as weather_service

MAX_DAYS = 14


class TripInvalid(Exception):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Invalid trip")
        self.fields = fields


def find(db: Session, user: User, trip_id: uuid.UUID) -> Trip | None:
    return db.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))


def listed(db: Session, user: User) -> list[Trip]:
    return list(
        db.scalars(
            select(Trip)
            .where(Trip.user_id == user.id)
            .order_by(Trip.start_date.desc(), Trip.created_at.desc())
        )
    )


def items_of(db: Session, trip: Trip) -> list[uuid.UUID]:
    return list(db.scalars(select(TripItem.item_id).where(TripItem.trip_id == trip.id)))


def create(db: Session, user: User, provider: WeatherProvider, fields: dict[str, Any]) -> Trip:
    """Plan a trip and its packing list."""
    days = _days(db, fields)
    trip = Trip(
        user_id=user.id,
        destination=fields["destination"],
        latitude=fields.get("latitude"),
        longitude=fields.get("longitude"),
        start_date=fields["start_date"],
        end_date=fields["end_date"],
        days=days,
    )
    packing = _plan(db, user, provider, trip)
    db.add(trip)
    db.flush()
    _write_items(db, trip, packing)
    return trip


def replan(db: Session, user: User, provider: WeatherProvider, trip: Trip) -> None:
    """Plan the packing again from the wardrobe as it is now."""
    packing = _plan(db, user, provider, trip)
    db.execute(delete(TripItem).where(TripItem.trip_id == trip.id))
    _write_items(db, trip, packing)


def set_packed(
    db: Session, user: User, trip: Trip, item_ids: list[uuid.UUID], packed: bool
) -> None:
    """Packed items leave everyday suggestions; unpacking makes them available again."""
    on_list = set(items_of(db, trip))
    if any(item_id not in on_list for item_id in item_ids):
        raise TripInvalid({"item_ids": "Those items aren't on this trip's list."})
    for item in db.scalars(select(Item).where(Item.user_id == user.id, Item.id.in_(item_ids))):
        if packed and item.status == "available":
            item.status = "packed"
        elif not packed and item.status == "packed":
            item.status = "available"
    db.flush()


def remove(db: Session, user: User, trip: Trip) -> None:
    """Delete the trip; anything still marked packed for it is unpacked."""
    set_packed(db, user, trip, items_of(db, trip), packed=False)
    db.delete(trip)
    db.flush()


def _days(db: Session, fields: dict[str, Any]) -> list[dict[str, Any]]:
    problems = {}
    start: date = fields["start_date"]
    end: date = fields["end_date"]
    if end < start:
        problems["end_date"] = "The trip ends before it starts."
    elif (end - start).days + 1 > MAX_DAYS:
        problems["end_date"] = f"Plan up to {MAX_DAYS} days at a time."
    known = reference.known_ids(db, Occasion)
    if fields["occasion_id"] not in known:
        problems["occasion_id"] = "Choose one of the options shown."
    overrides: dict[date, str] = fields.get("day_occasions") or {}
    if any(occasion not in known for occasion in overrides.values()):
        problems["day_occasions"] = "Choose one of the options shown."
    if any(not start <= day <= end for day in overrides):
        problems["day_occasions"] = "Those days aren't in the trip."
    if problems:
        raise TripInvalid(problems)
    return [
        {
            "day": (start + timedelta(days=n)).isoformat(),
            "occasion_id": overrides.get(start + timedelta(days=n), fields["occasion_id"]),
        }
        for n in range((end - start).days + 1)
    ]


def _plan(db: Session, user: User, provider: WeatherProvider, trip: Trip) -> list[str]:
    """Work out the packing; the trip keeps the day outfits, the ids to pack are returned."""
    profile = profiles.get_or_create_profile(db, user)
    dates = [date.fromisoformat(day["day"]) for day in trip.days]
    weather = weather_service.for_days(
        db, provider, profile, dates, latitude=trip.latitude, longitude=trip.longitude
    )
    wardrobe = suggestions.load_wardrobe(db, user, dates[0])
    # Items packed for this trip are still at hand for it.
    wardrobe = replace(
        wardrobe,
        items=tuple(
            replace(item, status="available") if item.status == "packed" else item
            for item in wardrobe.items
        ),
    )
    base = suggestions.base_context(db, user, profile, wardrobe, dates[0])
    occasions = {row.id: suggestions.engine_occasion(row) for row in db.scalars(select(Occasion))}
    packing = pack(
        wardrobe,
        base,
        [
            TripDay(
                day=day,
                occasion=occasions[entry["occasion_id"]],
                weather=weather[day].for_engine(),
                season=season_for(day),
            )
            for day, entry in zip(dates, trip.days, strict=True)
        ],
        DEFAULT,
        suggestions.pair_cache_for(user),
    )
    trip.engine_version = packing.engine_version
    trip.outfits = [
        {
            "day": packed.day.isoformat(),
            "item_ids": [item.id for item in packed.outfit.items] if packed.outfit else [],
            "core_ids": list(packed.outfit.core_ids) if packed.outfit else [],
            "score": packed.outfit.score if packed.outfit else None,
            "reasons": [
                {"code": reason.code, "kind": reason.kind, "text": reason.text}
                for reason in (packed.outfit.reasons if packed.outfit else ())
            ],
            "missing": [missing.text for missing in packed.missing],
            "weather": weather[packed.day].snapshot(),
        }
        for packed in packing.days
    ]
    return list(packing.item_ids)


def _write_items(db: Session, trip: Trip, item_ids: list[str]) -> None:
    for item_id in item_ids:
        db.add(TripItem(trip_id=trip.id, item_id=uuid.UUID(item_id)))
    db.flush()
