"""Email in WearWise (docs/AGENTS.md, section 7; D57): the weekly email only after the address
is confirmed, links that work without logging in but only for what they were made for,
one-click unsubscribe from a mail app, and a new password by email."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from conftest import CSRF_HEADER, TEST_PASSWORD
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_digests import a_trend, dresses_for_college

from app.adapters.email import Email, FakeEmail
from app.core.config import ConfigError, get_settings
from app.models import Digest, DigestPick, User
from app.services import digest_email, email_links, email_tokens, mail, subscriptions
from app.services import password_reset as resets

SETTINGS = "/api/v1/digest-settings"
NOW = datetime.now(UTC)


def link_token(letter: Email, path: str) -> str:
    found = re.search(rf"{re.escape(path)}\?token=([\w\-.]+)", letter.text)
    assert found, f"no {path} link in the email"
    return found.group(1)


def user(db: Session, email: str = "sam@example.com") -> User:
    return db.scalars(select(User).where(User.email == email)).one()


def use_settings(monkeypatch: pytest.MonkeyPatch, **changes: Any) -> None:
    settings = get_settings().model_copy(update=changes)
    for module in (subscriptions, mail, email_links, digest_email, resets):
        monkeypatch.setattr(module, "get_settings", lambda: settings)


def test_the_weekly_email_comes_on_only_once_the_address_is_confirmed(
    sam: TestClient, outbox: FakeEmail
) -> None:
    asked = sam.post(f"{SETTINGS}/on", json={"weekday": 4}).json()

    [letter] = outbox.sent
    token = link_token(letter, "/confirm-email")
    confirmed = sam.post("/api/v1/auth/confirm-email", json={"token": token})
    after = sam.get(SETTINGS).json()
    again = sam.post("/api/v1/auth/confirm-email", json={"token": token})

    assert (asked["on"], asked["waiting_for_confirmation"], asked["weekday"]) == (False, True, 4)
    assert letter.to == "sam@example.com"
    assert letter.subject == "Confirm your address for WearWise's weekly email"
    assert confirmed.status_code == 204
    assert (after["on"], after["confirmed"], after["waiting_for_confirmation"]) == (
        True,
        True,
        False,
    )
    # A link works once.
    assert again.status_code == 400


def test_a_confirmed_address_turns_on_at_once_and_can_change_day_and_turn_off(
    db: Session, sam: TestClient, outbox: FakeEmail
) -> None:
    user(db).email_verified_at = NOW
    db.flush()

    on = sam.post(f"{SETTINGS}/on", json={}).json()
    friday = sam.patch(SETTINGS, json={"weekday": 4}).json()
    off = sam.post(f"{SETTINGS}/off").json()

    assert outbox.sent == []
    assert on["on"] and friday["weekday"] == 4 and not off["on"]
    assert sam.patch(SETTINGS, json={"weekday": 7}).status_code == 422


def test_a_demo_never_gets_email(client: TestClient, outbox: FakeEmail) -> None:
    client.post("/api/v1/auth/demo", json={"section": "menswear"})

    answer = client.post(f"{SETTINGS}/on", json={})

    assert answer.status_code == 409 and answer.json()["error"]["code"] == "demo_account"
    assert outbox.sent == []


def test_until_a_domain_is_verified_an_unlisted_address_is_told_so(
    sam: TestClient, outbox: FakeEmail, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_settings(monkeypatch, email_allowlist="owner@example.com")

    state = sam.get(SETTINGS).json()
    answer = sam.post(f"{SETTINGS}/on", json={})

    assert state["preview_only"] is True
    assert answer.status_code == 409
    assert answer.json()["error"]["code"] == "email_preview_only"
    assert outbox.sent == []


def a_weekly_email(db: Session, sam: TestClient) -> tuple[Email, Digest]:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    built = sam.post("/api/v1/digests/preview").json()
    found = db.get_one(Digest, built["id"])
    return digest_email.render(db, found, user(db)), found


def test_the_weekly_email_says_what_the_page_says_with_no_photos(
    db: Session, sam: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_settings(monkeypatch, app_url="https://wearwise.example")
    letter, digest = a_weekly_email(db, sam)
    [pick] = db.scalars(select(DigestPick).where(DigestPick.digest_id == digest.id))

    assert letter.subject == digest.subject
    assert f"1. {pick.name}".upper() in letter.text
    assert pick.text in letter.text and "In fashion now: Olive chinos." in letter.text
    assert "you usually spend up to ₹1,500" in letter.text
    assert all(link["url"] in letter.text for link in pick.links)
    assert "https://wearwise.example/picks" in letter.text
    assert "<img" not in letter.html
    assert letter.key == f"digest-{digest.id}"
    assert letter.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert letter.headers["List-Unsubscribe"].startswith(
        "<https://wearwise.example/api/v1/email/unsubscribe/one-click?token="
    )


def test_until_a_domain_is_verified_the_weekly_email_says_its_a_preview(
    db: Session, sam: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_settings(monkeypatch, email_allowlist="owner@example.com")
    letter, digest = a_weekly_email(db, sam)

    assert letter.subject == "Preview: " + digest.subject
    assert letter.text.startswith("A preview:")


def test_a_mail_apps_unsubscribe_button_works_without_a_login_or_the_header(
    app: FastAPI, db: Session, sam: TestClient
) -> None:
    user(db).email_verified_at = NOW
    sam.post(f"{SETTINGS}/on", json={})
    letter, _ = a_weekly_email(db, sam)
    url = letter.headers["List-Unsubscribe"].strip("<>")
    path = url[url.index("/api/v1/") :]

    with TestClient(app) as mail_app:
        clicked = mail_app.post(
            path, content="List-Unsubscribe=One-Click", headers={"content-type": "text/plain"}
        )

    assert clicked.status_code == 204
    assert sam.get(SETTINGS).json()["on"] is False


def test_the_unsubscribe_and_not_for_me_links_do_only_what_they_say(
    db: Session, sam: TestClient
) -> None:
    user(db).email_verified_at = NOW
    sam.post(f"{SETTINGS}/on", json={})
    letter, digest = a_weekly_email(db, sam)
    not_for_me = link_token(letter, "/not-for-me")
    unsubscribe = link_token(letter, "/unsubscribe")

    swapped = [
        sam.post("/api/v1/email/unsubscribe", json={"token": not_for_me}).status_code,
        sam.post("/api/v1/email/not-for-me", json={"token": unsubscribe}).status_code,
        sam.post("/api/v1/email/unsubscribe", json={"token": unsubscribe + "x"}).status_code,
    ]
    declined = sam.post("/api/v1/email/not-for-me", json={"token": not_for_me})
    stopped = sam.post("/api/v1/email/unsubscribe", json={"token": unsubscribe})

    assert swapped == [400, 400, 400]
    assert sam.get(SETTINGS).json()["on"] is False
    assert (declined.status_code, stopped.status_code) == (204, 204)
    [pick] = db.scalars(select(DigestPick).where(DigestPick.digest_id == digest.id))
    assert pick.verdict == "not_for_me"


def test_production_never_signs_links_without_its_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = email_links.sign("unsubscribe", "someone")
    use_settings(monkeypatch, app_env="production", email_link_secret=None)

    assert email_links.verify(token, "unsubscribe") is None
    with pytest.raises(ConfigError, match="EMAIL_LINK_SECRET"):
        email_links.sign("unsubscribe", "someone")


def test_a_new_password_by_email(
    app: FastAPI, db: Session, sam: TestClient, outbox: FakeEmail
) -> None:
    sam.post("/api/v1/auth/password-reset", json={"email": " SAM@example.com "})
    [letter] = outbox.sent
    token = link_token(letter, "/reset-password")

    weak = sam.post("/api/v1/auth/password-reset/confirm", json={"token": token, "password": "x"})
    done = sam.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "a brand new long password"},
    )
    again = sam.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "another long password here"},
    )

    assert letter.subject == "Set a new WearWise password"
    assert weak.status_code == 422
    assert done.status_code == 204 and again.status_code == 400
    # Every session is logged out, the old password stops working, and the new one works.
    assert sam.get("/api/v1/auth/me").status_code == 401
    with TestClient(app, headers=CSRF_HEADER) as fresh:
        old = fresh.post(
            "/api/v1/auth/login", json={"email": "sam@example.com", "password": TEST_PASSWORD}
        )
        new = fresh.post(
            "/api/v1/auth/login",
            json={"email": "sam@example.com", "password": "a brand new long password"},
        )
    assert (old.status_code, new.status_code) == (401, 200)
    assert user(db).email_verified_at is not None


def test_asking_for_a_reset_says_the_same_whoever_asks(
    client: TestClient, sam: TestClient, outbox: FakeEmail
) -> None:
    nobody = client.post("/api/v1/auth/password-reset", json={"email": "nobody@example.com"})
    client.post("/api/v1/auth/demo", json={"section": "menswear"})
    demo_email = client.get("/api/v1/auth/me").json()["email"]
    demo = client.post("/api/v1/auth/password-reset", json={"email": demo_email})

    assert (nobody.status_code, demo.status_code) == (204, 204)
    assert outbox.sent == []


def test_asking_for_a_reset_is_limited_per_address(client: TestClient, sam: TestClient) -> None:
    codes = [
        client.post("/api/v1/auth/password-reset", json={"email": "sam@example.com"}).status_code
        for _ in range(4)
    ]

    assert codes == [204, 204, 204, 429]


def test_links_expire_and_asking_again_stops_the_old_one(db: Session, sam: TestClient) -> None:
    person = user(db)
    first = email_tokens.issue(db, person, "password_reset", NOW)
    second = email_tokens.issue(db, person, "password_reset", NOW)

    assert email_tokens.redeem(db, first, "password_reset", NOW) is None
    assert email_tokens.redeem(db, second, "password_reset", NOW + timedelta(hours=2)) is None
    third = email_tokens.issue(db, person, "password_reset", NOW)
    assert email_tokens.redeem(db, third, "confirm_email", NOW) is None
    assert email_tokens.redeem(db, third, "password_reset", NOW) == person


def test_rupees_are_grouped_the_indian_way() -> None:
    assert digest_email.rupees(150000) == "₹1,500"
    assert digest_email.rupees(15000000) == "₹1,50,000"
    assert digest_email.rupees(123456789050) == "₹1,23,45,67,890.50"
    assert digest_email.rupees(99900) == "₹999"


def test_production_without_an_email_provider_sends_nothing_and_logs_no_address(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from app.adapters.email import ConsoleEmail, EmailUnavailable

    letter = Email(
        to="sam@example.com", subject="Set a new WearWise password", text="token", html=""
    )
    with pytest.raises(EmailUnavailable) as raised:
        ConsoleEmail(production=True).send(letter)

    assert raised.value.reason == "not_set_up"
    assert "sam@example.com" not in caplog.text and "token" not in caplog.text


def test_production_without_an_email_provider_says_the_email_isnt_ready(
    db: Session, sam: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_settings(monkeypatch, app_env="production", email_provider="console", email_allowlist="")

    assert subscriptions.state(db, user(db), NOW).preview_only is True
