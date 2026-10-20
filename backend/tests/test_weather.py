import io
import json
import urllib.error
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.adapters.weather import DayForecast, FakeWeather, OpenMeteo, WeatherUnavailable
from app.models import WeatherForecast
from app.services import weather as weather_service
from app.services.wear import today

PUNE = {"city": "Pune, Maharashtra, India", "latitude": 18.5196, "longitude": 73.8554}


@pytest.fixture(autouse=True)
def no_remembered_outages() -> Iterator[None]:
    weather_service.forget_failures()
    yield
    weather_service.forget_failures()


class Answer(io.BytesIO):
    def __enter__(self) -> Answer:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def serve(monkeypatch: pytest.MonkeyPatch, *answers: object) -> list[str]:
    """Make urlopen give these answers in turn: a dict (as JSON) or an exception."""
    asked: list[str] = []
    queue = list(answers)

    def urlopen(request: Any, timeout: float) -> Answer:
        asked.append(request.full_url)
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return Answer(json.dumps(answer).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return asked


FORECAST = {
    "daily": {
        "time": ["2026-10-20", "2026-10-21", "2026-10-22"],
        "apparent_temperature_max": [35.0, 33.1, None],
        "apparent_temperature_min": [27.8, 24.7, None],
        "precipitation_probability_max": [15, 60, None],
    }
}


def test_open_meteo_forecasts_are_read_and_empty_days_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = serve(monkeypatch, FORECAST)

    days = OpenMeteo().forecast(18.5196, 73.8554)

    assert [(d.day.isoformat(), d.feels_like_max, d.rain_chance) for d in days] == [
        ("2026-10-20", 35.0, 15),
        ("2026-10-21", 33.1, 60),
    ]
    assert "latitude=18.52" in asked[0] and "longitude=73.86" in asked[0]


def test_a_server_error_is_retried_once(monkeypatch: pytest.MonkeyPatch) -> None:
    down = urllib.error.HTTPError("u", 503, "down", None, None)  # type: ignore[arg-type]
    asked = serve(monkeypatch, down, FORECAST)

    assert len(OpenMeteo().forecast(1, 2)) == 2
    assert len(asked) == 2


def test_a_bad_request_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    wrong = urllib.error.HTTPError("u", 400, "bad", None, None)  # type: ignore[arg-type]
    asked = serve(monkeypatch, wrong, FORECAST)

    with pytest.raises(WeatherUnavailable):
        OpenMeteo().forecast(1, 2)
    assert len(asked) == 1


def test_timeouts_twice_mean_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch, TimeoutError("slow"), TimeoutError("slow"))

    with pytest.raises(WeatherUnavailable):
        OpenMeteo().forecast(1, 2)


def test_places_are_labelled_town_region_country(monkeypatch: pytest.MonkeyPatch) -> None:
    serve(
        monkeypatch,
        {
            "results": [
                {
                    "name": "Pune",
                    "admin1": "Maharashtra",
                    "country": "India",
                    "latitude": 18.51957,
                    "longitude": 73.85535,
                }
            ]
        },
    )

    (place,) = OpenMeteo().places("Pune")

    assert place.label == "Pune, Maharashtra, India"


def test_searching_places(sam: TestClient) -> None:
    found = sam.get("/api/v1/places", params={"q": "pune"})

    assert found.status_code == 200
    assert found.json()[0]["label"] == "Pune, Maharashtra, India"
    assert sam.get("/api/v1/places", params={"q": "p"}).status_code == 422


def test_place_search_down_says_so(sam: TestClient, weather: FakeWeather) -> None:
    weather.fail = True

    response = sam.get("/api/v1/places", params={"q": "pune"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "places_unavailable"


def test_place_search_needs_a_login(client: TestClient) -> None:
    assert client.get("/api/v1/places", params={"q": "pune"}).status_code == 401


def test_choosing_a_place_stores_rounded_coordinates(sam: TestClient) -> None:
    profile = sam.patch("/api/v1/profile", json=PUNE).json()

    assert (profile["city"], profile["latitude"], profile["longitude"]) == (
        "Pune, Maharashtra, India",
        18.52,
        73.86,
    )
    cleared = sam.patch("/api/v1/profile", json={"city": None}).json()
    assert (cleared["latitude"], cleared["longitude"]) == (None, None)


def test_half_a_place_is_refused(sam: TestClient) -> None:
    response = sam.patch("/api/v1/profile", json={"city": "Pune", "latitude": 18.5})

    assert response.status_code == 422
    assert response.json()["error"]["fields"]["city"] == "Choose the place from the search results."


def test_the_usual_week_takes_known_occasions_for_real_weekdays(sam: TestClient) -> None:
    ok = sam.patch("/api/v1/profile", json={"weekday_occasions": {"0": "college", "6": "home"}})
    bad_day = sam.patch("/api/v1/profile", json={"weekday_occasions": {"7": "college"}})
    bad_occasion = sam.patch("/api/v1/profile", json={"weekday_occasions": {"1": "brunch"}})

    assert ok.json()["weekday_occasions"] == {"0": "college", "6": "home"}
    assert bad_day.status_code == 422
    assert bad_occasion.status_code == 422


def test_the_forecast_is_fetched_once_a_day_and_shared(
    sam: TestClient, ana: TestClient, weather: FakeWeather, db: Session
) -> None:
    sam.patch("/api/v1/profile", json=PUNE)
    ana.patch("/api/v1/profile", json=PUNE)

    first = sam.get("/api/v1/weather", params={"days": 3}).json()
    sam.get("/api/v1/weather")
    ana.get("/api/v1/weather")

    assert weather.calls == 1
    assert db.scalar(select(func.count()).select_from(WeatherForecast)) == 1
    assert [day["source"] for day in first] == ["forecast"] * 3
    # The middle of the day's feels-like range.
    assert first[0]["feels_like"] == 24.5
    assert first[0]["rain_chance"] == 10


def test_without_a_forecast_the_manual_setting_then_the_season(
    sam: TestClient, weather: FakeWeather
) -> None:
    weather.fail = True
    sam.patch("/api/v1/profile", json=PUNE)

    by_season = sam.get("/api/v1/weather").json()[0]
    sam.patch("/api/v1/profile", json={"manual_weather": "rainy"})
    manual = sam.get("/api/v1/weather").json()[0]

    assert (by_season["source"], by_season["feels_like"]) == ("season", None)
    assert (manual["source"], manual["feels_like"], manual["rain_chance"]) == ("manual", 27.0, 80)


def test_an_outage_is_remembered_so_pages_stay_quick(sam: TestClient, weather: FakeWeather) -> None:
    weather.fail = True
    sam.patch("/api/v1/profile", json=PUNE)

    sam.get("/api/v1/weather")
    sam.get("/api/v1/weather")

    assert weather.calls == 1


def test_days_past_the_forecast_use_the_manual_setting(
    sam: TestClient, weather: FakeWeather
) -> None:
    weather.days = weather.days[:2]
    sam.patch("/api/v1/profile", json={**PUNE, "manual_weather": "hot"})

    days = sam.get("/api/v1/weather", params={"days": 4}).json()

    assert [day["source"] for day in days] == ["forecast", "forecast", "manual", "manual"]


def test_a_cold_forecast_reaches_the_suggestions(sam: TestClient, weather: FakeWeather) -> None:
    weather.days = [DayForecast(today() + timedelta(days=n), 8.0, 4.0, 10) for n in range(3)]
    sam.patch("/api/v1/profile", json=PUNE)
    add_item(sam, "tshirt", "white")
    add_item(sam, "shorts", "navy")
    add_item(sam, "sneakers", "white")

    found = sam.post("/api/v1/outfits/suggest", json={"occasion_id": "home"}).json()

    texts = [reason["text"] for reason in found["suggestions"][0]["reasons"]]
    assert "The navy shorts may feel cold at 6°." in texts
