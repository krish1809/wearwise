"""Weather forecasts and place search. One interface, two implementations:

- OpenMeteo: the free Open-Meteo forecast and geocoding APIs, over HTTPS with a timeout and one
  retry. Forecast data is CC BY 4.0 from Open-Meteo.com; place search is based on GeoNames.
  The app credits both in its footer. The free tier is for non-commercial use.
- FakeWeather: canned answers, for tests and for working offline (WEATHER_PROVIDER=fake).

Callers cache forecasts (one request per place per day) and fall back to the person's manual
setting when this raises WeatherUnavailable.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import get_settings

log = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
TIMEOUT_SECONDS = 5
# One retry at most, as for every external call.
ATTEMPTS = 2
# Open-Meteo forecasts up to 16 days ahead; one fetch covers a week's plan and most trips.
FORECAST_DAYS = 16


class WeatherUnavailable(Exception):
    """The weather service didn't answer, or answered with something unusable."""


@dataclass(frozen=True)
class DayForecast:
    day: date
    # Feels-like (apparent) temperature, °C.
    feels_like_max: float
    feels_like_min: float
    # Highest chance of rain in the day, 0 to 100.
    rain_chance: int


@dataclass(frozen=True)
class Place:
    name: str
    region: str | None
    country: str | None
    latitude: float
    longitude: float

    @property
    def label(self) -> str:
        """ "Pune, Maharashtra, India"."""
        return ", ".join(part for part in (self.name, self.region, self.country) if part)


class WeatherProvider(Protocol):
    def forecast(self, latitude: float, longitude: float) -> list[DayForecast]:
        """Today and the days after it, as far as the service forecasts."""
        ...

    def places(self, query: str) -> list[Place]:
        """Places matching a name, most likely first."""
        ...


class OpenMeteo:
    def forecast(self, latitude: float, longitude: float) -> list[DayForecast]:
        data = _get(
            FORECAST_URL,
            {
                "latitude": f"{latitude:.2f}",
                "longitude": f"{longitude:.2f}",
                "daily": "apparent_temperature_max,apparent_temperature_min,"
                "precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": FORECAST_DAYS,
            },
        )
        try:
            daily = data["daily"]
            return [
                DayForecast(
                    day=date.fromisoformat(day),
                    feels_like_max=float(high),
                    feels_like_min=float(low),
                    rain_chance=int(rain or 0),
                )
                for day, high, low, rain in zip(
                    daily["time"],
                    daily["apparent_temperature_max"],
                    daily["apparent_temperature_min"],
                    daily["precipitation_probability_max"],
                    strict=True,
                )
                # The last days can come back empty; leave them out.
                if high is not None and low is not None
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise WeatherUnavailable(f"Unexpected forecast: {error}") from error

    def places(self, query: str) -> list[Place]:
        data = _get(GEOCODING_URL, {"name": query, "count": 8, "language": "en", "format": "json"})
        try:
            return [
                Place(
                    name=row["name"],
                    region=row.get("admin1"),
                    country=row.get("country"),
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                )
                for row in data.get("results", [])
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise WeatherUnavailable(f"Unexpected place search answer: {error}") from error


def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "WearWise (personal wardrobe app)"},
    )
    last: Exception | None = None
    for _ in range(ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                found: dict[str, Any] = json.loads(response.read())
                return found
        except urllib.error.HTTPError as error:
            last = error
            if error.code < 500:
                break  # our request was wrong; asking again won't help
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last = error
    log.warning("Weather service unavailable: %s", last)
    raise WeatherUnavailable(str(last))


@dataclass
class FakeWeather:
    """Canned forecasts and places. `fail` makes every call raise, like a service that's down."""

    days: list[DayForecast] = field(default_factory=list)
    found: list[Place] = field(default_factory=list)
    fail: bool = False
    calls: int = 0

    @classmethod
    def mild(cls, start: date, count: int = FORECAST_DAYS) -> FakeWeather:
        return cls(
            days=[DayForecast(start + timedelta(days=n), 28.0, 21.0, 10) for n in range(count)],
            found=[Place("Pune", "Maharashtra", "India", 18.52, 73.86)],
        )

    def forecast(self, latitude: float, longitude: float) -> list[DayForecast]:
        self.calls += 1
        if self.fail:
            raise WeatherUnavailable("fake outage")
        return list(self.days)

    def places(self, query: str) -> list[Place]:
        self.calls += 1
        if self.fail:
            raise WeatherUnavailable("fake outage")
        return [place for place in self.found if query.lower() in place.label.lower()]


@lru_cache
def get_weather() -> WeatherProvider:
    if get_settings().weather_provider == "fake":
        return FakeWeather.mild(date.today())
    return OpenMeteo()
