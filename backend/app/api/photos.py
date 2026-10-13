"""Photo uploads, and the photos themselves, only for the person who uploaded them."""

import uuid
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, File, Response, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.adapters.storage import StorageError
from app.api.deps import CurrentUser, SessionDep, SettingsDep, StorageDep
from app.api.errors import ApiError, error_responses
from app.models import ItemImage
from app.services import photos, rate_limit

router = APIRouter(prefix="/photos", tags=["photos"])

UPLOADS_PER_USER = rate_limit.Limit(attempts=120, window=timedelta(hours=1))
# A link to a photo in the bucket works for this long; the browser keeps it a little less.
LINK_SECONDS = 600


class PhotoOut(BaseModel):
    id: uuid.UUID
    url: str
    thumb_url: str
    width: int
    height: int
    # The main colour measured in the photo, and the nearest colour family.
    dominant_hex: str | None
    suggested_color: str | None

    @classmethod
    def build(cls, image: ItemImage, suggested: str | None = None) -> PhotoOut:
        return cls(
            id=image.id,
            url=f"/api/v1/photos/{image.id}/full",
            thumb_url=f"/api/v1/photos/{image.id}/thumb",
            width=image.width,
            height=image.height,
            dominant_hex=image.dominant_hex,
            suggested_color=suggested,
        )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PhotoOut,
    responses=error_responses(401, 403, 413, 422, 429, 503),
)
def upload_photo(
    file: Annotated[UploadFile, File(description="A JPEG, PNG, or WebP photo")],
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> PhotoOut:
    """Upload a photo before saving the item, so the colour can be suggested from it."""
    try:
        rate_limit.hit(db, f"upload:user:{user.id}", UPLOADS_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(429, "rate_limited", "Too many uploads. Try again in an hour.") from error
    db.commit()

    # The server has the whole upload by now, so its size is known before reading it.
    oversized = photos.too_large(file.size or 0, settings.max_upload_mb)
    if oversized:
        raise ApiError(413, "photo_too_large", oversized, fields={"file": oversized})
    # One byte past the limit is enough to catch a file whose size wasn't reported.
    data = file.file.read(settings.max_upload_mb * photos.MB + 1)
    try:
        processed = photos.process(data, settings.max_upload_mb)
    except photos.PhotoRejected as error:
        message = str(error)
        raise ApiError(422, "photo_rejected", message, fields={"file": message}) from error

    stale = photos.remove_unattached(db, user)
    try:
        image = photos.save_upload(db, storage, user, processed)
    except StorageError as error:
        db.rollback()
        raise ApiError(
            503, "storage_unavailable", "Couldn't save the photo. Try again in a moment."
        ) from error
    suggested = photos.suggest_family(db, processed.dominant_hex)
    db.commit()
    storage.delete(stale)
    return PhotoOut.build(image, suggested)


@router.get(
    "/{photo_id}/{size}",
    response_class=Response,
    responses={
        200: {"content": {"image/webp": {}}, "description": "The photo"},
        307: {"description": "A short-lived link to the photo in storage"},
        **error_responses(401, 404),
    },
)
def get_photo(
    photo_id: uuid.UUID,
    size: Literal["thumb", "full"],
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
) -> Response:
    """The photo, if it's this person's. Anyone else gets the same 404 as for no photo."""
    image = photos.find_photo(db, user, photo_id)
    if image is None:
        raise ApiError(404, "photo_not_found", "That photo doesn't exist.")
    key = image.thumb_key if size == "thumb" else image.storage_key
    link = storage.link(key, LINK_SECONDS)
    if link is not None:
        return RedirectResponse(
            link,
            status_code=307,
            headers={"Cache-Control": f"private, max-age={LINK_SECONDS - 60}"},
        )
    data = storage.get(key)
    if data is None:
        raise ApiError(404, "photo_not_found", "That photo doesn't exist.")
    # A key is never reused, so the file under it never changes.
    return Response(
        data,
        media_type="image/webp",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )
