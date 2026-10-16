"""Register, log in, log out, and who is logged in."""

import hashlib
import uuid
from datetime import timedelta

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep, SettingsDep, client_ip
from app.api.errors import ApiError, error_responses
from app.api.session_cookie import SESSION_COOKIE, clear_session_cookie, set_session_cookie
from app.models.user import User
from app.services import auth, rate_limit
from app.services.password_policy import password_problem

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_PER_EMAIL = rate_limit.Limit(attempts=10, window=timedelta(minutes=15))
LOGIN_PER_IP = rate_limit.Limit(attempts=30, window=timedelta(minutes=15))
REGISTER_PER_IP = rate_limit.Limit(attempts=10, window=timedelta(hours=1))


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None
    # False until onboarding is finished or skipped; logging in resumes it until then.
    onboarding_completed: bool
    # Demo accounts are made only by the demo script; the app labels them.
    is_demo: bool


class RegisterRequest(BaseModel):
    email: str = Field(max_length=320)
    # Argon2 takes any length; the cap only keeps requests small.
    password: str = Field(max_length=1024)
    name: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        try:
            checked = validate_email(value.strip(), check_deliverability=False)
        except EmailNotValidError as error:
            raise ValueError("Enter an email address like sam@example.com.") from error
        return auth.normalize_email(checked.normalized)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        problem = password_problem(value)
        if problem:
            raise ValueError(problem)
        return value

    @field_validator("name")
    @classmethod
    def tidy_name(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


def _limit(db: Session, bucket: str, limit: rate_limit.Limit) -> None:
    """Count the attempt and commit it, so it counts even if the request then fails."""
    try:
        rate_limit.hit(db, bucket, limit)
    except rate_limit.RateLimited as error:
        db.commit()
        minutes = max(1, round(error.retry_after_seconds / 60))
        raise ApiError(
            429,
            "rate_limited",
            f"Too many attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    db.commit()


def _email_bucket(action: str, email: str) -> str:
    # Hashed, so the rate-limit table doesn't hold email addresses.
    return f"{action}:email:{hashlib.sha256(email.encode()).hexdigest()[:24]}"


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
    responses=error_responses(403, 409, 422, 429),
)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: SessionDep,
    settings: SettingsDep,
) -> User:
    """Create an account and log in."""
    _limit(db, f"register:ip:{client_ip(request)}", REGISTER_PER_IP)
    try:
        user = auth.register(db, email=body.email, password=body.password, name=body.name)
    except auth.EmailTaken as error:
        message = "An account with this email already exists. Log in instead."
        raise ApiError(409, "email_taken", message, fields={"email": message}) from error
    token = auth.start_session(
        db, user, days=settings.session_days, user_agent=request.headers.get("user-agent")
    )
    db.commit()
    set_session_cookie(response, token, settings)
    return user


@router.post("/login", response_model=UserOut, responses=error_responses(401, 403, 422, 429))
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: SessionDep,
    settings: SettingsDep,
) -> User:
    """Log in. A wrong password and an unknown email get the same answer."""
    email = auth.normalize_email(body.email)
    _limit(db, _email_bucket("login", email), LOGIN_PER_EMAIL)
    _limit(db, f"login:ip:{client_ip(request)}", LOGIN_PER_IP)
    user = auth.authenticate(db, email=email, password=body.password)
    if user is None:
        raise ApiError(
            401,
            "invalid_credentials",
            "That email and password don't match an account. Check them and try again.",
        )
    token = auth.start_session(
        db, user, days=settings.session_days, user_agent=request.headers.get("user-agent")
    )
    db.commit()
    set_session_cookie(response, token, settings)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=error_responses(403))
def logout(request: Request, response: Response, db: SessionDep, settings: SettingsDep) -> None:
    """End this session. Safe to call when already logged out."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        auth.end_session(db, token)
        db.commit()
    clear_session_cookie(response, settings)


@router.get("/me", response_model=UserOut, responses=error_responses(401))
def me(user: CurrentUser) -> User:
    """Who is logged in."""
    return user
