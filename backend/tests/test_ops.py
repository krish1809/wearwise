"""Request ids, logs, errors recorded on both sides, and the owner's page of counts."""

import json
import logging
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.core.config import Settings, get_settings
from app.core.logs import JsonFormatter, request_id
from app.models import ErrorEvent

STATS = "/api/v1/admin/stats"
REPORTS = "/api/v1/client-errors"


def test_every_answer_has_a_request_id_and_keeps_a_sensible_one_it_was_sent(
    client: TestClient,
) -> None:
    made = client.get("/api/v1/health").headers["x-request-id"]
    kept = client.get("/api/v1/health", headers={"X-Request-ID": "browser-1234abcd"})
    replaced = client.get("/api/v1/health", headers={"X-Request-ID": "<script>"})

    assert len(made) == 16
    assert kept.headers["x-request-id"] == "browser-1234abcd"
    assert replaced.headers["x-request-id"] != "<script>"


def test_an_unexpected_error_is_recorded_and_answered_with_its_reference(
    app: FastAPI, client: TestClient, db: Session
) -> None:
    @app.get("/api/v1/broken/{thing_id}")
    def broken(thing_id: str) -> None:
        raise RuntimeError("the database said no")

    response = client.get("/api/v1/broken/abc?q=private", headers={"X-Request-ID": "trace-9876"})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "server_error"
    assert "reference trace-9876" in response.json()["error"]["message"]
    # Nothing about what broke reaches the person, and the 500 has the usual headers.
    assert "database" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    found = db.scalar(select(ErrorEvent).where(ErrorEvent.request_id == "trace-9876"))
    assert found is not None
    assert (found.source, found.kind, found.status) == ("server", "RuntimeError", 500)
    assert found.path == "/api/v1/broken/{thing_id}"
    assert found.detail and "the database said no" in found.detail


def test_each_request_is_logged_by_its_route_without_ids_or_the_query(
    sam: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    item = add_item(sam, "chinos", "navy")
    with caplog.at_level(logging.INFO, logger="app.requests"):
        sam.get(f"/api/v1/items/{item['id']}?note=private", headers={"X-Request-ID": "log-12345"})

    [line] = [
        r
        for r in caplog.records
        if r.name == "app.requests" and r.fields["method"] == "GET"  # type: ignore[attr-defined]
    ]
    fields: dict[str, Any] = line.fields  # type: ignore[attr-defined]
    assert (fields["method"], fields["path"], fields["status"]) == (
        "GET",
        "/api/v1/items/{item_id}",
        200,
    )
    assert isinstance(fields["ms"], int)


def test_production_logs_are_one_json_object_per_line() -> None:
    record = logging.LogRecord("app.requests", logging.INFO, __file__, 1, "request", None, None)
    record.fields = {"path": "/api/v1/items", "status": 200}
    token = request_id.set("json-1234")
    try:
        line = JsonFormatter().format(record)
    finally:
        request_id.reset(token)

    entry = json.loads(line)
    assert entry["message"] == "request" and entry["level"] == "info"
    assert (entry["request_id"], entry["path"], entry["status"]) == (
        "json-1234",
        "/api/v1/items",
        200,
    )


def test_the_browser_can_report_an_error_without_an_account(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api import ops
    from app.services import rate_limit

    monkeypatch.setattr(ops, "REPORTS_PER_IP", rate_limit.Limit(2, timedelta(hours=1)))
    report = {"message": "x is undefined", "path": "/wardrobe?q=red#top", "stack": "at Grid"}

    first = client.post(REPORTS, json=report)
    long = client.post(REPORTS, json={**report, "message": "x" * 3000})
    second = client.post(REPORTS, json=report)
    over = client.post(REPORTS, json=report)

    assert (first.status_code, long.status_code, second.status_code) == (204, 422, 204)
    assert over.status_code == 429
    stored = db.scalars(select(ErrorEvent).where(ErrorEvent.source == "browser")).all()
    assert [(e.path, e.message, e.detail) for e in stored][-1] == (
        "/wardrobe",
        "x is undefined",
        "at Grid",
    )


def as_admin(app: FastAPI, email: str) -> None:
    settings: Settings = get_settings().model_copy(update={"admin_emails": f" {email} ,"})
    app.dependency_overrides[get_settings] = lambda: settings


def test_only_the_owner_sees_the_counts(app: FastAPI, sam: TestClient, ana: TestClient) -> None:
    as_admin(app, "SAM@example.com".lower())
    add_item(sam, "chinos", "navy")
    add_item(ana, "casual_shirt", "white")

    theirs = ana.get(STATS)
    mine = sam.get(STATS)

    # The same answer as a page that doesn't exist, so nobody learns there is one.
    assert theirs.status_code == 404
    assert mine.status_code == 200
    counts = mine.json()
    assert (counts["users"], counts["items"], counts["photos"], counts["outfits"]) == (2, 2, 0, 0)
    assert counts["ai_daily_cap_usd"] == get_settings().ai_daily_spend_cap_usd


def test_acceptance_counts_each_suggestion_once(app: FastAPI, sam: TestClient) -> None:
    as_admin(app, "sam@example.com")
    sam.patch("/api/v1/profile", json={"occasion_ids": ["college"]})
    for category, colour in [
        ("casual_shirt", "white"),
        ("casual_shirt", "navy"),
        ("chinos", "beige"),
        ("loafers", "brown"),
    ]:
        add_item(sam, category, colour, fabric="cotton")
    shown = sam.post("/api/v1/outfits/suggest", json={"occasion_id": "college", "count": 2}).json()[
        "suggestions"
    ]
    first = shown[0]["id"]
    sam.post(f"/api/v1/suggestions/{first}/feedback", json={"verdict": "like"})
    sam.post(f"/api/v1/suggestions/{first}/save", json={})

    [row] = sam.get(STATS).json()["acceptance"]

    assert (row["shown"], row["liked"], row["saved"], row["accepted"]) == (len(shown), 1, 1, 1)
