"""Place search, to pick the city the weather comes from."""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.adapters.weather import WeatherUnavailable
from app.api.deps import CurrentUser, SessionDep, WeatherDep
from app.api.errors import ApiError, error_responses
from app.services import profile as profiles
from app.services import rate_limit, wear
from app.services import weather as weather_service

router = APIRouter(tags=["weather"])

SEARCHES_PER_USER = rate_limit.Limit(attempts=60, window=timedelta(hours=1))
MAX_DAYS = 16


class PlaceOut(BaseModel):
    # "Pune, Maharashtra, India".
    label: str
    name: str
    region: str | None
    country: str | None
    latitude: float
    longitude: float


class DayWeatherOut(BaseModel):
    day: date
    # forecast (Open-Meteo), manual (the person's setting), or season (nothing else known).
    source: Literal["forecast", "manual", "season"]
    # Feels-like °C for the day; null when going by the season.
    feels_like: float | None
    # Chance of rain, 0 to 100; null when going by the season.
    rain_chance: int | None


@router.get("/places", response_model=list[PlaceOut], responses=error_responses(401, 422, 429, 503))
def search_places(
    q: Annotated[str, Query(min_length=2, max_length=100)],
    user: CurrentUser,
    db: SessionDep,
    provider: WeatherDep,
) -> list[PlaceOut]:
    """Places matching a name, most likely first. Location data is based on GeoNames."""
    try:
        rate_limit.hit(db, f"places:user:{user.id}", SEARCHES_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(
            429, "rate_limited", "That's a lot of searches. Try again a little later."
        ) from error
    # No outside call inside a database transaction.
    db.commit()
    try:
        found = provider.places(q.strip())
    except WeatherUnavailable as error:
        raise ApiError(
            503, "places_unavailable", "Place search isn't answering. Try again in a moment."
        ) from error
    return [
        PlaceOut(
            label=place.label,
            name=place.name,
            region=place.region,
            country=place.country,
            latitude=place.latitude,
            longitude=place.longitude,
        )
        for place in found
    ]


@router.get("/weather", response_model=list[DayWeatherOut], responses=error_responses(401, 422))
def get_weather(
    user: CurrentUser,
    db: SessionDep,
    provider: WeatherDep,
    start: date | None = None,
    days: Annotated[int, Query(ge=1, le=MAX_DAYS)] = 1,
) -> list[DayWeatherOut]:
    """The weather for the days from `start` (today by default): the forecast for the
    profile's city, else the manual setting, else nothing but the season."""
    first = start or wear.today()
    profile = profiles.get_or_create_profile(db, user)
    found = weather_service.for_days(
        db, provider, profile, [first + timedelta(days=n) for n in range(days)]
    )
    db.commit()
    return [
        DayWeatherOut(
            day=day.day, source=day.source, feels_like=day.feels_like, rain_chance=day.rain_chance
        )
        for day in found.values()
    ]
