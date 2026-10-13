from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.session_cookie import SESSION_COOKIE
from app.core.security import hash_session_token
from app.models.user_session import UserSession
from app.services import auth

PASSWORD = "correct horse battery staple"
CSRF_HEADER = {"X-Requested-With": "test"}


def make_user(db: Session, email: str = "sam@example.com", password: str = PASSWORD) -> None:
    """Create an account directly, without going through the sign-up form's password rules."""
    auth.register(db, email=email, password=password, name="Sam Lee")
    db.commit()


def log_in(client: TestClient, email: str = "sam@example.com", password: str = PASSWORD) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


# Registering


def test_register_creates_an_account_and_logs_in(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "  Sam@Example.COM ", "password": PASSWORD, "name": " Sam Lee "},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "sam@example.com"
    assert response.json()["name"] == "Sam Lee"
    assert client.get("/api/v1/auth/me").json()["email"] == "sam@example.com"


def test_register_with_a_taken_email_says_so(client: TestClient, db: Session) -> None:
    make_user(db)

    response = client.post(
        "/api/v1/auth/register", json={"email": "SAM@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"
    assert "email" in response.json()["error"]["fields"]


def test_register_rejects_a_password_the_policy_rejects(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register", json={"email": "sam@example.com", "password": "short"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["fields"]["password"]


def test_register_rejects_a_malformed_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register", json={"email": "not-an-email", "password": PASSWORD}
    )

    assert response.status_code == 422
    assert response.json()["error"]["fields"]["email"] == (
        "Enter an email address like sam@example.com."
    )


# Logging in and out


def test_login_with_the_right_password_starts_a_session(client: TestClient, db: Session) -> None:
    make_user(db)

    log_in(client, email="  SAM@example.com")

    assert client.cookies.get(SESSION_COOKIE)
    assert client.get("/api/v1/auth/me").json()["name"] == "Sam Lee"


def test_wrong_password_and_unknown_email_get_the_same_answer(
    client: TestClient, db: Session
) -> None:
    make_user(db)

    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "sam@example.com", "password": "not it at all"}
    )
    unknown_email = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["code"] == "invalid_credentials"


def test_logout_ends_the_session(client: TestClient, db: Session) -> None:
    make_user(db)
    log_in(client)
    token = client.cookies.get(SESSION_COOKIE)

    assert client.post("/api/v1/auth/logout").status_code == 204

    client.cookies.set(SESSION_COOKIE, token or "")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_expired"


# Sessions


def test_a_protected_route_rejects_an_anonymous_request(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_an_expired_session_is_rejected(client: TestClient, db: Session) -> None:
    make_user(db)
    log_in(client)
    db.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Your session has ended. Log in again."
    # The stale cookie is removed too.
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_only_a_hash_of_the_session_token_is_stored(client: TestClient, db: Session) -> None:
    make_user(db)
    log_in(client)
    token = client.cookies.get(SESSION_COOKIE) or ""

    stored = db.scalars(select(UserSession.token_hash)).all()

    assert stored == [hash_session_token(token)]
    assert token not in stored


def test_each_session_belongs_to_its_own_user(app: FastAPI, db: Session) -> None:
    make_user(db, email="sam@example.com")
    make_user(db, email="ana@example.com")

    with (
        TestClient(app, headers=CSRF_HEADER) as sam,
        TestClient(app, headers=CSRF_HEADER) as ana,
    ):
        log_in(sam, email="sam@example.com")
        log_in(ana, email="ana@example.com")

        assert sam.get("/api/v1/auth/me").json()["email"] == "sam@example.com"
        assert ana.get("/api/v1/auth/me").json()["email"] == "ana@example.com"


# Protection


def test_too_many_login_attempts_are_refused(client: TestClient, db: Session) -> None:
    make_user(db)
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"email": "sam@example.com", "password": "wrong"})

    response = client.post(
        "/api/v1/auth/login", json={"email": "sam@example.com", "password": PASSWORD}
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert int(response.headers["Retry-After"]) > 0


def test_a_state_changing_request_without_the_custom_header_is_refused(app: FastAPI) -> None:
    with TestClient(app) as bare:
        response = bare.post(
            "/api/v1/auth/login", json={"email": "sam@example.com", "password": PASSWORD}
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "missing_header"
