"""The week's plan: a day's occasion (chosen, an event, or the usual one for that weekday),
its weather, and an outfit for it from the planner (app/engine/planner.py).

Locked days and days already worn keep their outfits when the week is planned again; the
planner counts their wears. Marking a day as worn logs it through the wear log, the same path
as "I wore this today".
"""

import uuid
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.weather import WeatherProvider
from app.engine.config import DEFAULT, ENGINE_VERSION
from app.engine.generate import score_outfit, season_for
from app.engine.planner import DaySpec, Locked, alternatives, plan_week
from app.engine.types import ScoredOutfit
from app.models import Event, Occasion, PlanDay, Profile, User, WearLog
from app.services import events as event_service
from app.services import profile as profiles
from app.services import suggestions, wear
from app.services import weather as weather_service
from app.services.weather import DayWeather

WEEK = 7
ALTERNATIVES = 6

OccasionSource = Literal["chosen", "event", "usual", "none"]


class PlanInvalid(Exception):
    def __init__(
        self, fields: dict[str, str], message: str = "Check the highlighted fields."
    ) -> None:
        super().__init__(message)
        self.fields = fields
        self.message = message


@dataclass
class Day:
    """One day of the week as the page shows it."""

    day: date
    # The occasion in force: chosen for the day, an event's, or the weekday's usual one.
    occasion_id: str | None
    # Where it came from: chosen for the day, an event, the usual one, or none yet.
    occasion_source: OccasionSource
    events: list[Event]
    weather: DayWeather
    row: PlanDay | None

    @property
    def outdated(self) -> bool:
        """Planned for a different occasion than the day now has."""
        return (
            self.row is not None
            and bool(self.row.item_ids)
            and self.row.wear_log_id is None
            and self.row.planned_occasion_id != self.occasion_id
        )


def days_from(start: date) -> list[date]:
    return [start + timedelta(days=n) for n in range(WEEK)]


def week(
    db: Session, user: User, provider: WeatherProvider, start: date
) -> tuple[Profile, list[Day]]:
    """The seven days from start, with whatever has been planned for them."""
    profile = profiles.get_or_create_profile(db, user)
    dates = days_from(start)
    # First: the forecast may end the read transaction to ask the weather service.
    weather = weather_service.for_days(db, provider, profile, dates)
    rows = {
        row.day: row
        for row in db.scalars(
            select(PlanDay).where(
                PlanDay.user_id == user.id, PlanDay.day >= dates[0], PlanDay.day <= dates[-1]
            )
        )
    }
    by_day: dict[date, list[Event]] = {}
    for event in event_service.between(db, user, dates[0], dates[-1]):
        by_day.setdefault(event.day, []).append(event)
    found = []
    for day in dates:
        row = rows.get(day)
        occasion, source = occasion_for(profile, by_day.get(day, []), day, row)
        found.append(Day(day, occasion, source, by_day.get(day, []), weather[day], row))
    return profile, found


def occasion_for(
    profile: Profile, events: list[Event], day: date, row: PlanDay | None
) -> tuple[str | None, OccasionSource]:
    if row is not None and row.occasion_id:
        return row.occasion_id, "chosen"
    if events:
        return events[0].occasion_id, "event"
    usual = profile.weekday_occasions.get(str(day.weekday()))
    if usual:
        return usual, "usual"
    if profile.occasion_ids:
        return profile.occasion_ids[0], "usual"
    return None, "none"


def generate(db: Session, user: User, provider: WeatherProvider, start: date) -> list[Day]:
    """Plan every day from start that isn't locked or worn; keep the rest."""
    profile, days = week(db, user, provider, start)
    wardrobe = suggestions.load_wardrobe(db, user, start)
    base = suggestions.base_context(db, user, profile, wardrobe, start)
    specs = _specs(db, days)
    plan = plan_week(
        wardrobe,
        base,
        specs,
        DEFAULT,
        suggestions.pair_cache_for(user),
        laundry_weekday=profile.laundry_weekday,
    )
    for entry, planned in zip(days, plan.days, strict=True):
        if planned.locked:
            continue
        row = entry.row or _new_row(db, user, entry.day)
        _store(row, planned.outfit, entry)
        row.missing = [
            {"slot": missing.slot, "code": missing.code, "text": missing.text}
            for missing in planned.missing
        ]
        entry.row = row
    db.flush()
    return days


def options(
    db: Session, user: User, provider: WeatherProvider, start: date, day: date
) -> list[ScoredOutfit]:
    """Other outfits for one day that keep the rest of the week within the rules."""
    profile, days = week(db, user, provider, start)
    target = _one(days, day)
    if target.occasion_id is None:
        raise PlanInvalid({"occasion_id": "Choose an occasion for this day first."})
    wardrobe = suggestions.load_wardrobe(db, user, start)
    base = suggestions.base_context(db, user, profile, wardrobe, start)
    # Every other planned day is kept as it is.
    specs = [
        replace(spec, locked=None) if entry.day == day else spec
        for entry, spec in zip(days, _specs(db, days, lock_all=True), strict=True)
    ]
    found = alternatives(
        wardrobe,
        base,
        specs,
        day,
        ALTERNATIVES + 1,
        DEFAULT,
        suggestions.pair_cache_for(user),
        laundry_weekday=profile.laundry_weekday,
    )
    current = {str(item_id) for item_id in target.row.core_ids} if target.row else set()
    return [outfit for outfit in found if set(outfit.core_ids) != current][:ALTERNATIVES]


def change(
    db: Session,
    user: User,
    provider: WeatherProvider,
    start: date,
    day: date,
    fields: dict[str, Any],
) -> Day:
    """Lock or unlock a day, choose its occasion, or swap in another outfit (which locks it,
    so planning the week again keeps the choice)."""
    profile, days = week(db, user, provider, start)
    target = _one(days, day)
    row = target.row or _new_row(db, user, day)
    target.row = row
    if "occasion_id" in fields:
        row.occasion_id = fields["occasion_id"]
        target.occasion_id, target.occasion_source = occasion_for(profile, target.events, day, row)
    if fields.get("item_ids") is not None:
        if row.wear_log_id is not None:
            message = "This day is already worn. Change it in the wear log."
            raise PlanInvalid({"item_ids": message}, message)
        wardrobe = suggestions.load_wardrobe(db, user, start)
        base = suggestions.base_context(db, user, profile, wardrobe, start)
        occasion = db.get(Occasion, target.occasion_id) if target.occasion_id else None
        context = replace(
            base,
            today=day,
            occasion=suggestions.engine_occasion(occasion) if occasion else None,
            weather=target.weather.for_engine(),
            season=season_for(day),
        )
        outfit = score_outfit(
            wardrobe,
            context,
            [str(item_id) for item_id in fields["item_ids"]],
            DEFAULT,
            suggestions.pair_cache_for(user),
        )
        if outfit is None:
            message = "Those pieces don't make a whole outfit from your wardrobe."
            raise PlanInvalid({"item_ids": message}, message)
        _store(row, outfit, target)
        row.missing = []
        row.locked = True
    if fields.get("locked") is not None:
        row.locked = fields["locked"]
    db.flush()
    return target


def wear_day(db: Session, user: User, provider: WeatherProvider, day: date) -> Day:
    """Log the day's outfit as worn, once; the plan keeps it from then on."""
    _, days = week(db, user, provider, day)
    target = days[0]
    row = target.row
    if row is None or not row.item_ids:
        raise PlanInvalid(
            {"day": "Nothing is planned for this day."}, "Nothing is planned for this day."
        )
    if row.wear_log_id is not None and db.get(WearLog, row.wear_log_id) is not None:
        return target
    log, _ = wear.log_wear(
        db,
        user,
        worn_on=day,
        outfit_id=None,
        item_ids=list(row.item_ids),
        occasion_id=target.occasion_id,
        note=None,
    )
    row.wear_log_id = log.id
    db.flush()
    return target


def _specs(db: Session, days: list[Day], *, lock_all: bool = False) -> list[DaySpec]:
    occasions = {
        occasion.id: suggestions.engine_occasion(occasion)
        for occasion in db.scalars(select(Occasion))
    }
    found = []
    for entry in days:
        row = entry.row
        keep = (
            row is not None
            and bool(row.item_ids)
            and (row.locked or row.wear_log_id is not None or lock_all)
        )
        found.append(
            DaySpec(
                day=entry.day,
                occasion=occasions.get(entry.occasion_id) if entry.occasion_id else None,
                weather=entry.weather.for_engine(),
                season=season_for(entry.day),
                locked=(
                    Locked(
                        tuple(str(item_id) for item_id in row.item_ids),
                        tuple(str(item_id) for item_id in row.core_ids),
                    )
                    if keep and row is not None
                    else None
                ),
            )
        )
    return found


def _one(days: list[Day], day: date) -> Day:
    for entry in days:
        if entry.day == day:
            return entry
    raise PlanInvalid({"day": "That day isn't in this week."}, "That day isn't in this week.")


def _new_row(db: Session, user: User, day: date) -> PlanDay:
    row = PlanDay(user_id=user.id, day=day, item_ids=[], core_ids=[], reasons=[], missing=[])
    db.add(row)
    return row


def _store(row: PlanDay, outfit: ScoredOutfit | None, entry: Day) -> None:
    row.planned_occasion_id = entry.occasion_id
    row.weather = entry.weather.snapshot()
    row.engine_version = ENGINE_VERSION
    row.wear_log_id = None
    if outfit is None:
        row.template_id = None
        row.item_ids = []
        row.core_ids = []
        row.score = None
        row.reasons = []
        return
    row.template_id = outfit.template_id
    row.item_ids = [uuid.UUID(item.id) for item in outfit.items]
    row.core_ids = [uuid.UUID(item_id) for item_id in outfit.core_ids]
    row.score = outfit.score
    row.reasons = [
        {"code": reason.code, "kind": reason.kind, "text": reason.text} for reason in outfit.reasons
    ]
