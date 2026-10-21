import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Index, Uuid, false
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class WeatherForecast(IdMixin, TimestampMixin, Base):
    """One day's fetch of the forecast for a place, shared by everyone near it. At most one
    request per place per day goes to the weather service."""

    __tablename__ = "weather_forecasts"

    # Rounded to two decimals (about a kilometre), so neighbours share a forecast.
    latitude: Mapped[float]
    longitude: Mapped[float]
    # The day it was fetched (UTC), and when.
    fetched_on: Mapped[date] = mapped_column(Date)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # [{date, feels_like_max, feels_like_min, rain_chance, code}], one per day ahead.
    days: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)


Index(
    "uq_weather_forecasts_place_day",
    WeatherForecast.latitude,
    WeatherForecast.longitude,
    WeatherForecast.fetched_on,
    unique=True,
)


class Event(IdMixin, TimestampMixin, Base):
    """Something on a given day with a dress code: it sets that day's occasion."""

    __tablename__ = "events"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    title: Mapped[str]
    occasion_id: Mapped[str] = mapped_column(ForeignKey("occasions.id"))
    note: Mapped[str | None]


Index("ix_events_user_id_day", Event.user_id, Event.day)


class PlanDay(IdMixin, TimestampMixin, Base):
    """One day of the week's plan: its occasion, weather, and the outfit chosen for it."""

    __tablename__ = "plan_days"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    # Set when the person chose an occasion for this day; otherwise it follows their usual
    # week and events.
    occasion_id: Mapped[str | None] = mapped_column(ForeignKey("occasions.id"))
    # The occasion the outfit was planned for; when the day's occasion changes, it's out of
    # date until planned again.
    planned_occasion_id: Mapped[str | None] = mapped_column(ForeignKey("occasions.id"))
    # The outfit, as a suggestion is kept: plain arrays, so a deleted item makes it stale.
    template_id: Mapped[str | None] = mapped_column(ForeignKey("outfit_templates.id"))
    item_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), server_default="{}")
    core_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), server_default="{}")
    score: Mapped[float | None]
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="[]")
    # Why nothing could be planned, when nothing was: [{slot, code, text}].
    missing: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="[]")
    # Locked days keep their outfit when the rest of the week is planned again.
    locked: Mapped[bool] = mapped_column(default=False, server_default=false())
    # Set once it's worn; worn days are kept like locked ones. Deleting the log un-wears it.
    wear_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("wear_logs.id", ondelete="SET NULL")
    )
    # The weather it was planned for: {feels_like, rain_chance, source}.
    weather: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    engine_version: Mapped[str | None]


Index("uq_plan_days_user_id_day", PlanDay.user_id, PlanDay.day, unique=True)
# Deleting a wear log clears the planned day's link to it.
Index(
    "ix_plan_days_wear_log_id",
    PlanDay.wear_log_id,
    postgresql_where=PlanDay.wear_log_id.is_not(None),
)


class Trip(IdMixin, TimestampMixin, Base):
    """A trip to pack for: where, when, and the occasion of each day."""

    __tablename__ = "trips"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    destination: Mapped[str]
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    # [{day, occasion_id}], one per day of the trip.
    days: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    # The outfit for each day from the packed items: [{day, item_ids, core_ids, score,
    # reasons, weather}] or {day, missing} when a day couldn't be covered.
    outfits: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="[]")
    engine_version: Mapped[str | None]


class TripItem(IdMixin, TimestampMixin, Base):
    """An item on a trip's packing list."""

    __tablename__ = "trip_items"

    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), index=True
    )


Index("uq_trip_items_trip_id_item_id", TripItem.trip_id, TripItem.item_id, unique=True)
