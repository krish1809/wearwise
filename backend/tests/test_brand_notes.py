import pytest
from fastapi.testclient import TestClient

from app.services import brand_notes

NOTES = "/api/v1/brand-notes"


def test_notes_can_be_added_listed_edited_and_deleted(sam: TestClient) -> None:
    zara = sam.post(NOTES, json={"brand": " Zara ", "size_notes": "L in shirts"})
    sam.post(NOTES, json={"brand": "h&m", "size_notes": "M", "quality_notes": "  "})

    assert zara.status_code == 201
    note = zara.json()
    assert note["brand"] == "Zara"
    listed = sam.get(NOTES).json()
    assert [n["brand"] for n in listed] == ["h&m", "Zara"]
    assert listed[0]["quality_notes"] is None

    edited = sam.patch(f"{NOTES}/{note['id']}", json={"price_notes": "Waits for sales"})
    assert edited.status_code == 200
    assert edited.json()["size_notes"] == "L in shirts"
    assert edited.json()["price_notes"] == "Waits for sales"

    cleared = sam.patch(f"{NOTES}/{note['id']}", json={"size_notes": None, "brand": None})
    assert cleared.json()["size_notes"] is None
    assert cleared.json()["brand"] == "Zara"

    assert sam.delete(f"{NOTES}/{note['id']}").status_code == 204
    assert [n["brand"] for n in sam.get(NOTES).json()] == ["h&m"]


def test_a_second_note_for_the_same_brand_is_refused(sam: TestClient) -> None:
    sam.post(NOTES, json={"brand": "Levi's"})

    response = sam.post(NOTES, json={"brand": "LEVI'S"})

    assert response.status_code == 409
    assert response.json()["error"]["fields"]["brand"].startswith("You already have a note")


def test_renaming_onto_another_brand_is_refused(sam: TestClient) -> None:
    sam.post(NOTES, json={"brand": "Zara"})
    uniqlo = sam.post(NOTES, json={"brand": "Uniqlo"}).json()

    response = sam.patch(f"{NOTES}/{uniqlo['id']}", json={"brand": "zara"})

    assert response.status_code == 409
    assert [n["brand"] for n in sam.get(NOTES).json()] == ["Uniqlo", "Zara"]


def test_a_note_needs_a_brand(sam: TestClient) -> None:
    response = sam.post(NOTES, json={"brand": "   ", "size_notes": "M"})

    assert response.status_code == 422
    assert response.json()["error"]["fields"]["brand"] == "Enter the brand's name."


def test_the_number_of_notes_is_capped(sam: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(brand_notes, "MAX_NOTES", 2)
    sam.post(NOTES, json={"brand": "One"})
    sam.post(NOTES, json={"brand": "Two"})

    response = sam.post(NOTES, json={"brand": "Three"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "too_many_brand_notes"


def test_another_persons_notes_are_hidden_and_untouchable(sam: TestClient, ana: TestClient) -> None:
    note = sam.post(NOTES, json={"brand": "Zara", "size_notes": "L"}).json()

    assert ana.get(NOTES).json() == []
    assert ana.patch(f"{NOTES}/{note['id']}", json={"size_notes": "S"}).status_code == 404
    assert ana.delete(f"{NOTES}/{note['id']}").status_code == 404
    # The same brand can still have a note in another account.
    assert ana.post(NOTES, json={"brand": "Zara"}).status_code == 201
    assert sam.get(NOTES).json()[0]["size_notes"] == "L"


def test_brand_notes_need_a_login(client: TestClient) -> None:
    assert client.get(NOTES).status_code == 401
    assert client.post(NOTES, json={"brand": "Zara"}).status_code == 401
