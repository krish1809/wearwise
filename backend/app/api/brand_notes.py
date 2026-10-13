"""The person's brand notebook: "M in H&M, L in Zara"."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, status
from pydantic import AfterValidator, BaseModel, ConfigDict

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import ApiError, error_responses
from app.api.fields import NoteText, required_text
from app.models import BrandNote, User
from app.services import brand_notes

router = APIRouter(prefix="/brand-notes", tags=["brand notes"])

Brand = Annotated[str, AfterValidator(required_text(80, "Enter the brand's name."))]


class BrandNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand: str
    size_notes: str | None
    quality_notes: str | None
    price_notes: str | None
    updated_at: datetime


class BrandNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: Brand
    size_notes: NoteText = None
    quality_notes: NoteText = None
    price_notes: NoteText = None


class BrandNoteUpdate(BaseModel):
    """Only the fields sent are changed. Null clears a note; the brand can't be cleared."""

    model_config = ConfigDict(extra="forbid")

    brand: Brand | None = None
    size_notes: NoteText = None
    quality_notes: NoteText = None
    price_notes: NoteText = None


def _exists(brand: str) -> ApiError:
    message = f"You already have a note for {brand}. Edit that one instead."
    return ApiError(409, "brand_note_exists", message, fields={"brand": message})


def _owned(db: SessionDep, user: User, note_id: uuid.UUID) -> BrandNote:
    note = brand_notes.find_note(db, user, note_id)
    if note is None:
        # Someone else's note gets the same answer as one that doesn't exist.
        raise ApiError(404, "brand_note_not_found", "That brand note doesn't exist.")
    return note


@router.get("", response_model=list[BrandNoteOut], responses=error_responses(401))
def list_brand_notes(user: CurrentUser, db: SessionDep) -> list[BrandNote]:
    """Every note, A to Z. The list is capped, so it comes in one response."""
    return brand_notes.list_notes(db, user)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BrandNoteOut,
    responses=error_responses(401, 403, 409, 422),
)
def create_brand_note(body: BrandNoteCreate, user: CurrentUser, db: SessionDep) -> BrandNote:
    try:
        note = brand_notes.create_note(db, user, body.model_dump())
    except brand_notes.BrandNoteExists as error:
        raise _exists(body.brand) from error
    except brand_notes.TooManyBrandNotes as error:
        message = (
            f"You can keep up to {brand_notes.MAX_NOTES} brand notes. Delete one to add another."
        )
        raise ApiError(409, "too_many_brand_notes", message) from error
    db.commit()
    return note


@router.patch(
    "/{note_id}",
    response_model=BrandNoteOut,
    responses=error_responses(401, 403, 404, 409, 422),
)
def update_brand_note(
    note_id: uuid.UUID, body: BrandNoteUpdate, user: CurrentUser, db: SessionDep
) -> BrandNote:
    note = _owned(db, user, note_id)
    changes = body.model_dump(exclude_unset=True)
    if "brand" in changes and changes["brand"] is None:
        del changes["brand"]
    try:
        brand_notes.update_note(db, note, changes)
    except brand_notes.BrandNoteExists as error:
        raise _exists(changes["brand"]) from error
    db.commit()
    return note


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404),
)
def delete_brand_note(note_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> None:
    brand_notes.delete_note(db, _owned(db, user, note_id))
    db.commit()
