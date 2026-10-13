import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import ColorFamily, Occasion, VocabularyTerm
from app.services.reference_seed import SEED_DIR, SeedError, seed_reference_data


def seed(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((SEED_DIR / name).read_text())
    return data


def test_reference_lists_match_the_seed_files_in_order(sam: TestClient) -> None:
    response = sam.get("/api/v1/reference")

    assert response.status_code == 200
    body = response.json()
    taxonomy = seed("taxonomy.json")
    assert [c["id"] for c in body["color_families"]] == [
        c["id"] for c in seed("colors.json")["families"]
    ]
    assert [o["id"] for o in body["occasions"]] == [
        o["id"] for o in seed("occasions.json")["occasions"]
    ]
    assert [s["id"] for s in body["style_profiles"]] == [
        s["id"] for s in seed("style_profiles.json")["profiles"]
    ]
    assert [g["id"] for g in body["category_groups"]] == [g["id"] for g in taxonomy["groups"]]
    assert [t["id"] for t in body["sections"]] == taxonomy["sections"]
    assert [t["id"] for t in body["fits"]] == taxonomy["fits"]
    assert body["sizing_systems"] == taxonomy["sizing_systems"]


def test_reference_entries_carry_what_the_screens_show(sam: TestClient) -> None:
    body = sam.get("/api/v1/reference").json()

    multi = next(c for c in body["color_families"] if c["id"] == "multi")
    assert multi["hex"] is None
    minimal = next(s for s in body["style_profiles"] if s["id"] == "minimal")
    assert minimal["palette"] == seed("style_profiles.json")["profiles"][0]["signals"]["colors"]
    assert "signals" not in minimal
    assert {"id": "slim", "name": "Slim"} in body["fits"]


def test_reference_needs_a_login(client: TestClient) -> None:
    assert client.get("/api/v1/reference").status_code == 401


def test_seeding_again_changes_nothing(db: Session) -> None:
    changed = seed_reference_data(db)

    assert set(changed.values()) == {0}


def test_seeding_restores_edited_and_missing_rows(db: Session) -> None:
    db.execute(update(Occasion).where(Occasion.id == "home").values(name="Edited"))
    db.execute(
        delete(VocabularyTerm).where(VocabularyTerm.kind == "fit", VocabularyTerm.id == "slim")
    )

    changed = seed_reference_data(db)

    assert changed["occasions"] == 1
    assert changed["vocabulary_terms"] == 1
    assert db.scalar(select(Occasion.name).where(Occasion.id == "home")) == "At home"


def test_seeding_never_deletes_rows_missing_from_the_files(db: Session) -> None:
    db.add(ColorFamily(id="retired", name="Retired", hex="#000000", neutrality=0, position=99))
    db.flush()

    seed_reference_data(db)

    assert db.get(ColorFamily, "retired") is not None


@pytest.fixture
def seed_copy(tmp_path: Path) -> Path:
    for name in ("taxonomy.json", "colors.json", "occasions.json", "style_profiles.json"):
        shutil.copy(SEED_DIR / name, tmp_path / name)
    return tmp_path


def test_a_repeated_id_in_a_seed_file_is_refused(db: Session, seed_copy: Path) -> None:
    colors = json.loads((seed_copy / "colors.json").read_text())
    colors["families"].append(colors["families"][0])
    (seed_copy / "colors.json").write_text(json.dumps(colors))

    with pytest.raises(SeedError, match="black"):
        seed_reference_data(db, seed_copy)


def test_an_occasion_preferring_an_unknown_group_is_refused(db: Session, seed_copy: Path) -> None:
    occasions = json.loads((seed_copy / "occasions.json").read_text())
    occasions["occasions"][0]["prefers_groups"] = ["spacesuits"]
    (seed_copy / "occasions.json").write_text(json.dumps(occasions))

    with pytest.raises(SeedError, match="spacesuits"):
        seed_reference_data(db, seed_copy)
