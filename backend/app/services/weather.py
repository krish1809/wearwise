"""The weather for the days being dressed for: a cached forecast, the person's manual setting,
or the season.

A forecast is fetched at most once per place per day and shared by everyone near that place.
The fetch happens outside any database transaction (the read transaction is committed first),
and a failure is remembered for a while so pages stay quick while the service is down.
"""

import threading
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.adapters.weather import DayForecast, WeatherProvider, WeatherUnavailable
from app.engine.types import Weather
from app.models import Profile, WeatherForecast

Source = Literal["forecast", "manual", "season"]

# What each manual setting stands for: a feels-like temperature (°C) and a chance of rain.
MANUAL: dict[str, tuple[float, int]] = {
    "hot": (34.0, 10),
    "mild": (24.0, 10),
    "cold": (13.0, 10),
    "rainy": (27.0, 80),
}
# After a failed fetch, don't ask again for this long.
RETRY_AFTER = timedelta(minutes=30)

_failures: dict[tuple[float, float], datetime] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class DayWeather:
    day: date
    source: Source
    # Feels-like °C for the day (the middle of its range); None when going by the season.
    feels_like: float | None
    rain_chance: int | None

    def for_engine(self) -> Weather | None:
        if self.feels_like is None or self.rain_chance is None:
            return None
        return Weather(feels_like=self.feels_like, rain_chance=self.rain_chance)

    def snapshot(self) -> dict[str, object]:
        return {
            "source": self.source,
            "feels_like": self.feels_like,
            "rain_chance": self.rain_chance,
        }


def rounded(value: float) -> float:
    return round(value, 2)


def for_days(
    db: Session,
    provider: WeatherProvider,
    profile: Profile | None,
    days: list[date],
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[date, DayWeather]:
    """The weather for each day: a place given (a trip's destination) or the profile's city.

    Call this before changing anything in the request: it may commit the session to end the
    read transaction before asking the weather service."""
    if latitude is None or longitude is None:
        latitude = profile.latitude if profile else None
        longitude = profile.longitude if profile else None
    forecast: dict[date, DayForecast] = {}
    if latitude is not None and longitude is not None:
        forecast = {day.day: day for day in _forecast(db, provider, latitude, longitude)}
    manual = profile.manual_weather if profile else None
    found = {}
    for day in days:
        if day in forecast:
            entry = forecast[day]
            found[day] = DayWeather(
                day,
                "forecast",
                round((entry.feels_like_max + entry.feels_like_min) / 2, 1),
                entry.rain_chance,
            )
        elif manual in MANUAL:
            feels_like, rain = MANUAL[manual]
            found[day] = DayWeather(day, "manual", feels_like, rain)
        else:
            found[day] = DayWeather(day, "season", None, None)
    return found


def _forecast(
    db: Session, provider: WeatherProvider, latitude: float, longitude: float
) -> list[DayForecast]:
    place = (rounded(latitude), rounded(longitude))
    today = datetime.now(UTC).date()
    cached = db.scalar(
        select(WeatherForecast).where(
            WeatherForecast.latitude == place[0],
            WeatherForecast.longitude == place[1],
            WeatherForecast.fetched_on == today,
        )
    )
    if cached is not None:
        return [_day(row) for row in cached.days]
    with _lock:
        failed_at = _failures.get(place)
    if failed_at is not None and datetime.now(UTC) - failed_at < RETRY_AFTER:
        return []
    # No outside call while a database transaction is open.
    db.commit()
    try:
        days = provider.forecast(*place)
    except WeatherUnavailable:
        with _lock:
            _failures[place] = datetime.now(UTC)
        return []
    with _lock:
        _failures.pop(place, None)
    db.execute(
        insert(WeatherForecast)
        .values(
            latitude=place[0],
            longitude=place[1],
            fetched_on=today,
            fetched_at=datetime.now(UTC),
            days=[
                {
                    "date": day.day.isoformat(),
                    "feels_like_max": day.feels_like_max,
                    "feels_like_min": day.feels_like_min,
                    "rain_chance": day.rain_chance,
                }
                for day in days
            ],
        )
        # Two requests for the same place at once: the second keeps the first's row.
        .on_conflict_do_nothing()
    )
    db.flush()
    return days


def _day(row: dict[str, object]) -> DayForecast:
    return DayForecast(
        day=date.fromisoformat(str(row["date"])),
        feels_like_max=float(row["feels_like_max"]),  # type: ignore[arg-type]
        feels_like_min=float(row["feels_like_min"]),  # type: ignore[arg-type]
        rain_chance=int(row["rain_chance"]),  # type: ignore[call-overload]
    )


def forget_failures() -> None:
    """For tests: start with no remembered outages."""
    with _lock:
        _failures.clear()
