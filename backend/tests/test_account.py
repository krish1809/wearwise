from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession
from app.services import auth

PASSWORD = "correct horse battery staple"
CSRF_HEADER = {"X-Requested-With": "test"}


def make_user_and_log_in(db: Session, client: TestClient, email: str) -> None:
    auth.register(db, email=email, password=PASSWORD, name=None)
    db.commit()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200


def test_deleting_the_account_removes_the_user_and_their_sessions(
    client: TestClient, db: Session
) -> None:
    make_user_and_log_in(db, client, "sam@example.com")

    response = client.post("/api/v1/account/delete", json={"confirm_email": " SAM@example.com "})

    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0
    assert client.get("/api/v1/auth/me").status_code == 401
    login_again = client.post(
        "/api/v1/auth/login", json={"email": "sam@example.com", "password": PASSWORD}
    )
    assert login_again.status_code == 401


def test_a_wrong_confirmation_keeps_the_account(client: TestClient, db: Session) -> None:
    make_user_and_log_in(db, client, "sam@example.com")

    response = client.post("/api/v1/account/delete", json={"confirm_email": "someone@example.com"})

    assert response.status_code == 422
    assert response.json()["error"]["fields"]["confirm_email"]
    assert client.get("/api/v1/auth/me").status_code == 200


def test_deleting_one_account_leaves_another_untouched(app: FastAPI, db: Session) -> None:
    with (
        TestClient(app, headers=CSRF_HEADER) as sam,
        TestClient(app, headers=CSRF_HEADER) as ana,
    ):
        make_user_and_log_in(db, sam, "sam@example.com")
        make_user_and_log_in(db, ana, "ana@example.com")

        # Sam can't delete Ana's account by typing Ana's email: only the logged-in account goes.
        refused = sam.post("/api/v1/account/delete", json={"confirm_email": "ana@example.com"})
        deleted = sam.post("/api/v1/account/delete", json={"confirm_email": "sam@example.com"})

        assert refused.status_code == 422
        assert deleted.status_code == 204
        assert ana.get("/api/v1/auth/me").json()["email"] == "ana@example.com"


def test_deleting_needs_a_logged_in_person(client: TestClient) -> None:
    response = client.post("/api/v1/account/delete", json={"confirm_email": "sam@example.com"})

    assert response.status_code == 401


def test_the_name_can_be_changed_and_cleared(sam: TestClient) -> None:
    renamed = sam.patch("/api/v1/account", json={"name": "  Sam Lee "})

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Sam Lee"
    assert sam.get("/api/v1/auth/me").json()["name"] == "Sam Lee"
    assert sam.patch("/api/v1/account", json={"name": "  "}).json()["name"] is None


def test_the_email_cannot_be_changed_through_the_name_route(sam: TestClient) -> None:
    response = sam.patch("/api/v1/account", json={"email": "other@example.com"})

    assert response.status_code == 422
    assert sam.get("/api/v1/auth/me").json()["email"] == "sam@example.com"


def test_changing_the_name_needs_a_login(client: TestClient) -> None:
    assert client.patch("/api/v1/account", json={"name": "Sam"}).status_code == 401
