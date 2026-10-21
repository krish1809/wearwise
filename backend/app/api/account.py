"""The logged-in person's account."""

from collections.abc import Iterator
from datetime import timedelta

from fastapi import APIRouter, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import UserOut
from app.api.deps import CurrentUser, SessionDep, SettingsDep, StorageDep
from app.api.errors import ApiError, error_responses
from app.api.fields import ShortText
from app.api.session_cookie import clear_session_cookie
from app.models.user import User
from app.services import account, auth, export, rate_limit, wear

router = APIRouter(prefix="/account", tags=["account"])

# Building the file reads every photo, so it's limited.
EXPORTS_PER_USER = rate_limit.Limit(attempts=5, window=timedelta(hours=1))
CHUNK = 64 * 1024


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Blank clears the name. The email can't be changed here: that needs the password again.
    name: ShortText = None


class DeleteAccountRequest(BaseModel):
    # Typing the account's email confirms the person means it.
    confirm_email: str = Field(max_length=320)


@router.patch("", response_model=UserOut, responses=error_responses(401, 403, 422))
def update_account(body: AccountUpdate, user: CurrentUser, db: SessionDep) -> User:
    """Change the name WearWise greets you with."""
    if "name" in body.model_fields_set:
        user.name = body.name
    db.commit()
    return user


@router.post(
    "/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 422),
)
def delete_account(
    body: DeleteAccountRequest,
    response: Response,
    user: CurrentUser,
    db: SessionDep,
    settings: SettingsDep,
    storage: StorageDep,
) -> None:
    """Delete the account and everything in it, then log out."""
    if auth.normalize_email(body.confirm_email) != user.email:
        message = "That isn't this account's email address."
        raise ApiError(422, "confirmation_mismatch", message, fields={"confirm_email": message})
    account.delete_account(db, storage, user)
    clear_session_cookie(response, settings)


@router.get(
    "/export",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"application/zip": {}}, "description": "A zip file"},
        **error_responses(401, 429),
    },
)
def export_account(user: CurrentUser, db: SessionDep, storage: StorageDep) -> StreamingResponse:
    """Download everything stored for this account: every row, as JSON, and every photo."""
    try:
        rate_limit.hit(db, f"export:user:{user.id}", EXPORTS_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(
            429,
            "rate_limited",
            "You've downloaded your data a few times this hour. Try again later.",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    db.commit()
    archive = export.build(db, storage, user)

    def chunks() -> Iterator[bytes]:
        with archive:
            while chunk := archive.read(CHUNK):
                yield chunk

    name = f"wearwise-{wear.today().isoformat()}.zip"
    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
