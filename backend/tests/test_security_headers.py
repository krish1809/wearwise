from datetime import timedelta

import pytest
from fastapi.testclient import TestClient


def test_api_answers_carry_the_security_headers(client: TestClient) -> None:
    for response in (client.get("/api/v1/health"), client.get("/api/v1/items")):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"
        assert "default-src 'none'" in response.headers["content-security-policy"]


def test_photos_keep_their_own_caching(sam: TestClient) -> None:
    from photo_support import photo_bytes

    uploaded = sam.post(
        "/api/v1/photos", files={"file": ("shirt.jpg", photo_bytes(), "image/jpeg")}
    ).json()

    thumb = sam.get(uploaded["thumb_url"])

    assert thumb.headers["cache-control"] == "private, max-age=31536000, immutable"
    assert thumb.headers["x-content-type-options"] == "nosniff"


def test_the_api_docs_can_load_their_scripts(client: TestClient) -> None:
    assert "content-security-policy" not in client.get("/docs").headers


def test_every_change_counts_against_one_hourly_budget(
    sam: TestClient, ana: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api import deps
    from app.services import rate_limit

    monkeypatch.setattr(deps, "WRITES_PER_USER", rate_limit.Limit(3, timedelta(hours=1)))
    notes = "/api/v1/brand-notes"

    made = [sam.post(notes, json={"brand": f"Brand {n}"}).status_code for n in range(3)]
    over = sam.post(notes, json={"brand": "One too many"})

    assert made == [201, 201, 201]
    assert over.status_code == 429 and "Retry-After" in over.headers
    # Reading still works, and the budget is each person's own.
    assert sam.get(notes).status_code == 200
    assert ana.post(notes, json={"brand": "Brand 0"}).status_code == 201
