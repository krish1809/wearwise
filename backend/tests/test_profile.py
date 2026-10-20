from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BrandNote, Profile

PROFILE = "/api/v1/profile"


def test_a_new_account_starts_with_an_empty_profile(sam: TestClient) -> None:
    profile = sam.get(PROFILE).json()

    assert profile == {
        "sections": [],
        "city": None,
        "units": "cm",
        "currency": "INR",
        "height_cm": None,
        "measurements": {
            "chest": None,
            "waist": None,
            "hips": None,
            "shoulder": None,
            "inseam": None,
        },
        "sizes": {"top": None, "bottom": None, "shoe": None},
        "fit_preference": None,
        "style_profile_ids": [],
        "preferred_colors": [],
        "avoided_colors": [],
        "occasion_ids": [],
        "budget_monthly": None,
        "category_budgets": {},
        "onboarding_step": 0,
        "onboarding_skipped": False,
        "latitude": None,
        "longitude": None,
        "manual_weather": None,
        "weekday_occasions": {},
        "laundry_weekday": None,
        "show_onboarding_reminder": False,
    }
    assert sam.get("/api/v1/auth/me").json()["onboarding_completed"] is False


def test_skipping_everything_finishes_onboarding_with_an_empty_profile(sam: TestClient) -> None:
    response = sam.post("/api/v1/onboarding/finish", json={"skipped": True})

    assert response.status_code == 204
    assert sam.get("/api/v1/auth/me").json()["onboarding_completed"] is True
    profile = sam.get(PROFILE).json()
    assert profile["sections"] == []
    assert profile["show_onboarding_reminder"] is True


def test_the_reminder_goes_away_once_dismissed(sam: TestClient) -> None:
    sam.post("/api/v1/onboarding/finish", json={"skipped": True})

    response = sam.post("/api/v1/onboarding/reminder/dismiss")

    assert response.status_code == 204
    assert sam.get(PROFILE).json()["show_onboarding_reminder"] is False


def test_finishing_every_step_shows_no_reminder(sam: TestClient) -> None:
    sam.post("/api/v1/onboarding/finish", json={"skipped": True})

    sam.post("/api/v1/onboarding/finish", json={"skipped": False})

    profile = sam.get(PROFILE).json()
    assert profile["show_onboarding_reminder"] is False
    assert profile["onboarding_step"] == 6


def test_a_save_changes_only_the_fields_sent(sam: TestClient) -> None:
    sam.patch(PROFILE, json={"city": "  Pune ", "sections": ["menswear"]})

    response = sam.patch(PROFILE, json={"fit_preference": "relaxed", "onboarding_step": 2})

    assert response.status_code == 200
    profile = response.json()
    assert profile["city"] == "Pune"
    assert profile["sections"] == ["menswear"]
    assert profile["fit_preference"] == "relaxed"
    assert profile["onboarding_step"] == 2


def test_every_answer_can_be_cleared(sam: TestClient) -> None:
    sam.patch(
        PROFILE,
        json={
            "sections": ["menswear", "womenswear"],
            "city": "Pune",
            "height_cm": 175,
            "measurements": {"chest": 96, "waist": 81.3},
            "sizes": {"top": {"label": "M", "system": "in_uk"}, "shoe": {"label": "9"}},
            "fit_preference": "slim",
            "style_profile_ids": ["minimal"],
            "preferred_colors": ["navy"],
            "avoided_colors": ["orange"],
            "occasion_ids": ["college"],
            "budget_monthly": 300000,
            "category_budgets": {"tops": 150000},
        },
    )

    cleared = sam.patch(
        PROFILE,
        json={
            name: None
            for name in (
                "sections",
                "city",
                "height_cm",
                "measurements",
                "sizes",
                "fit_preference",
                "style_profile_ids",
                "preferred_colors",
                "avoided_colors",
                "occasion_ids",
                "budget_monthly",
                "category_budgets",
            )
        },
    ).json()

    assert cleared["sections"] == []
    assert cleared["city"] is None
    assert cleared["height_cm"] is None
    assert set(cleared["measurements"].values()) == {None}
    assert set(cleared["sizes"].values()) == {None}
    assert cleared["fit_preference"] is None
    assert cleared["style_profile_ids"] == cleared["preferred_colors"] == []
    assert cleared["avoided_colors"] == cleared["occasion_ids"] == []
    assert cleared["budget_monthly"] is None
    assert cleared["category_budgets"] == {}


def test_measurements_are_stored_in_cm_to_one_decimal(sam: TestClient, db: Session) -> None:
    # 32 inches, converted by the app before sending.
    sam.patch(PROFILE, json={"measurements": {"waist": 32 * 2.54}, "units": "in"})

    stored = db.scalars(select(Profile)).one()
    assert stored.measurements == {"waist": 81.3}
    assert stored.units == "in"


def test_a_measurement_outside_the_range_is_explained(sam: TestClient) -> None:
    response = sam.patch(PROFILE, json={"measurements": {"chest": 20}, "height_cm": 400})

    assert response.status_code == 422
    fields = response.json()["error"]["fields"]
    assert fields["measurements.chest"] == "Enter a number between 50 and 200 cm."
    assert fields["height_cm"] == "Enter a number between 50 and 250 cm."


def test_choices_must_come_from_the_reference_lists(sam: TestClient) -> None:
    response = sam.patch(
        PROFILE,
        json={
            "sections": ["kidswear"],
            "fit_preference": "baggy",
            "sizes": {"top": {"label": "M", "system": "jp"}},
            "style_profile_ids": ["unknown"],
            "preferred_colors": ["octarine"],
            "occasion_ids": ["moon_landing"],
            "category_budgets": {"cars": 100},
        },
    )

    assert response.status_code == 422
    assert set(response.json()["error"]["fields"]) == {
        "sections",
        "fit_preference",
        "sizes.top.system",
        "style_profile_ids",
        "preferred_colors",
        "occasion_ids",
        "category_budgets.cars",
    }
    assert sam.get(PROFILE).json()["sections"] == []


def test_a_colour_cannot_be_both_loved_and_avoided(sam: TestClient) -> None:
    sam.patch(PROFILE, json={"preferred_colors": ["navy"]})

    response = sam.patch(PROFILE, json={"avoided_colors": ["navy", "orange"]})

    assert response.status_code == 422
    assert "avoided_colors" in response.json()["error"]["fields"]


def test_repeated_choices_are_stored_once(sam: TestClient) -> None:
    profile = sam.patch(PROFILE, json={"occasion_ids": ["college", "work", "college"]}).json()

    assert profile["occasion_ids"] == ["college", "work"]


def test_unknown_fields_and_bad_amounts_are_refused(sam: TestClient) -> None:
    assert sam.patch(PROFILE, json={"user_id": "someone-else"}).status_code == 422
    assert sam.patch(PROFILE, json={"currency": "USD"}).status_code == 422
    negative = sam.patch(PROFILE, json={"budget_monthly": -1})
    assert negative.status_code == 422
    assert negative.json()["error"]["fields"]["budget_monthly"] == (
        "Enter an amount in rupees, up to ₹1,00,00,000."
    )
    assert sam.patch(PROFILE, json={"sizes": {"top": {"label": "  "}}}).status_code == 422


def test_one_persons_profile_is_invisible_to_another(sam: TestClient, ana: TestClient) -> None:
    sam.patch(PROFILE, json={"city": "Pune", "preferred_colors": ["navy"]})

    profile = ana.get(PROFILE).json()

    assert profile["city"] is None
    assert profile["preferred_colors"] == []


def test_profile_routes_need_a_login(client: TestClient) -> None:
    assert client.get(PROFILE).status_code == 401
    assert client.patch(PROFILE, json={"city": "Pune"}).status_code == 401
    assert client.post("/api/v1/onboarding/finish", json={"skipped": True}).status_code == 401
    assert client.post("/api/v1/onboarding/reminder/dismiss").status_code == 401


def test_deleting_the_account_removes_the_profile_and_brand_notes(
    sam: TestClient, db: Session
) -> None:
    sam.patch(PROFILE, json={"city": "Pune"})
    sam.post("/api/v1/brand-notes", json={"brand": "Zara", "size_notes": "L"})

    sam.post("/api/v1/account/delete", json={"confirm_email": "sam@example.com"})

    assert db.scalar(select(func.count()).select_from(Profile)) == 0
    assert db.scalar(select(func.count()).select_from(BrandNote)) == 0
