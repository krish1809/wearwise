"""The logged-in person's account."""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import UserOut
from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.api.errors import ApiError, error_responses
from app.api.fields import ShortText
from app.api.session_cookie import clear_session_cookie
from app.models.user import User
from app.services import account, auth

router = APIRouter(prefix="/account", tags=["account"])


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
) -> None:
    """Delete the account and everything in it, then log out."""
    if auth.normalize_email(body.confirm_email) != user.email:
        message = "That isn't this account's email address."
        raise ApiError(422, "confirmation_mismatch", message, fields={"confirm_email": message})
    account.delete_account(db, user)
    db.commit()
    clear_session_cookie(response, settings)
