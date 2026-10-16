"""The logged-in person's profile, and finishing or skipping onboarding."""

from typing import Annotated, Literal

from fastapi import APIRouter, status
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import ApiError, error_responses
from app.api.fields import Amount, IdList, ShortText, centimetres, required_text
from app.models import Profile
from app.services import profile as profiles

router = APIRouter(tags=["profile"])


class Measurements(BaseModel):
    """Body measurements in cm. The app converts to inches for display only."""

    model_config = ConfigDict(extra="forbid")

    chest: Annotated[float | None, AfterValidator(centimetres(50, 200))] = None
    waist: Annotated[float | None, AfterValidator(centimetres(40, 200))] = None
    hips: Annotated[float | None, AfterValidator(centimetres(50, 200))] = None
    shoulder: Annotated[float | None, AfterValidator(centimetres(25, 80))] = None
    inseam: Annotated[float | None, AfterValidator(centimetres(40, 120))] = None


class SizeChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # As written on the label ("M", "32", "9"). Never converted between systems.
    label: Annotated[
        str, AfterValidator(required_text(20, "Enter a size, or leave the whole size empty."))
    ]
    system: str | None = None


class Sizes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top: SizeChoice | None = None
    bottom: SizeChoice | None = None
    shoe: SizeChoice | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sections: list[str]
    city: str | None
    units: Literal["cm", "in"]
    currency: str
    height_cm: float | None
    measurements: Measurements
    sizes: Sizes
    fit_preference: str | None
    style_profile_ids: list[str]
    preferred_colors: list[str]
    avoided_colors: list[str]
    occasion_ids: list[str]
    # Minor units (paise).
    budget_monthly: int | None
    category_budgets: dict[str, int]
    onboarding_step: int
    onboarding_skipped: bool
    # True when Home should offer to finish setting up: onboarding was skipped, and the
    # reminder hasn't been dismissed.
    show_onboarding_reminder: bool

    @classmethod
    def build(cls, profile: Profile) -> ProfileOut:
        stored = {
            name: getattr(profile, name) for name in cls.model_fields if hasattr(profile, name)
        }
        reminder = profile.onboarding_skipped and profile.onboarding_reminder_dismissed_at is None
        return cls.model_validate({**stored, "show_onboarding_reminder": reminder})


class ProfileUpdate(BaseModel):
    """Only the fields sent are changed. Null clears a field."""

    model_config = ConfigDict(extra="forbid")

    sections: IdList = None
    city: ShortText = None
    units: Literal["cm", "in"] | None = None
    height_cm: Annotated[float | None, AfterValidator(centimetres(50, 250))] = None
    measurements: Measurements | None = None
    sizes: Sizes | None = None
    fit_preference: str | None = None
    style_profile_ids: IdList = None
    preferred_colors: IdList = None
    avoided_colors: IdList = None
    occasion_ids: IdList = None
    budget_monthly: Amount | None = None
    category_budgets: dict[str, Amount] | None = None
    onboarding_step: int | None = Field(default=None, ge=0, le=profiles.ONBOARDING_STEPS)


class FinishOnboardingRequest(BaseModel):
    # True for "Skip all": Home then offers, once, to finish setting up.
    skipped: bool


@router.get("/profile", response_model=ProfileOut, responses=error_responses(401))
def get_profile(user: CurrentUser, db: SessionDep) -> ProfileOut:
    profile = profiles.get_or_create_profile(db, user)
    db.commit()
    return ProfileOut.build(profile)


@router.patch("/profile", response_model=ProfileOut, responses=error_responses(401, 403, 422))
def update_profile(body: ProfileUpdate, user: CurrentUser, db: SessionDep) -> ProfileOut:
    """Change some answers. Send only the fields that changed; null clears one."""
    changes = body.model_dump(exclude_unset=True)
    for name in ("units", "onboarding_step"):
        # These always have a value; null leaves them as they are.
        if name in changes and changes[name] is None:
            del changes[name]
    for name in ("measurements", "sizes"):
        if changes.get(name) is not None:
            # Keep only the parts given, so the stored object has no null placeholders.
            changes[name] = getattr(body, name).model_dump(exclude_none=True)
    try:
        profile = profiles.update_profile(db, user, changes)
    except profiles.ProfileInvalid as error:
        raise ApiError(
            422, "invalid_input", "Check the highlighted fields.", fields=error.fields
        ) from error
    db.commit()
    return ProfileOut.build(profile)


@router.post(
    "/onboarding/finish",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 422),
)
def finish_onboarding(body: FinishOnboardingRequest, user: CurrentUser, db: SessionDep) -> None:
    """Mark onboarding done, whether every step was answered or skipped."""
    profiles.finish_onboarding(db, user, skipped=body.skipped)
    db.commit()


@router.post(
    "/onboarding/reminder/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403),
)
def dismiss_onboarding_reminder(user: CurrentUser, db: SessionDep) -> None:
    """Stop offering to finish setting up."""
    profiles.dismiss_onboarding_reminder(db, user)
    db.commit()
