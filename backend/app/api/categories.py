"""Categories: the seeded list, and the person's own additions."""

from typing import Annotated

from fastapi import APIRouter, status
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import ApiError, error_responses
from app.api.fields import required_text
from app.models import Category, CategoryGroup
from app.services import categories, reference

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    group_id: str
    slot: str
    # Sections that show it by default; empty for custom categories, which always show.
    sections: list[str]
    formality_default: int
    formality_min: int
    formality_max: int
    warmth: int
    wears_before_wash: int | None
    custom: bool

    @classmethod
    def build(cls, category: Category) -> CategoryOut:
        return cls.model_validate(
            {
                **{name: getattr(category, name) for name in cls.model_fields if name != "custom"},
                "custom": category.user_id is not None,
            }
        )


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, AfterValidator(required_text(60, "Enter a name for the category."))]
    group_id: str
    slot: str
    # Left out: smart casual (3), and light (1).
    formality_default: int | None = Field(default=None, ge=1, le=5)
    warmth: int | None = Field(default=None, ge=0, le=5)
    # Null when it isn't washed on a schedule.
    wears_before_wash: int | None = Field(default=1, ge=1, le=30)


@router.get("", response_model=list[CategoryOut], responses=error_responses(401))
def list_categories(user: CurrentUser, db: SessionDep) -> list[CategoryOut]:
    """Every category this person can use: the seeded ones, then their own."""
    return [CategoryOut.build(c) for c in categories.list_categories(db, user)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryOut,
    responses=error_responses(401, 403, 409, 422),
)
def create_category(body: CategoryCreate, user: CurrentUser, db: SessionDep) -> CategoryOut:
    """Add a category of the person's own, for something the list doesn't have."""
    problems: dict[str, str] = {}
    if body.group_id not in reference.known_ids(db, CategoryGroup):
        problems["group_id"] = "Choose one of the options shown."
    if body.slot not in reference.known_terms(db, "slot"):
        problems["slot"] = "Choose one of the options shown."
    if problems:
        raise ApiError(422, "invalid_input", "Check the highlighted fields.", fields=problems)
    try:
        category = categories.create_custom(db, user, body.model_dump())
    except categories.CategoryExists as error:
        message = f"You already have a category called {body.name}."
        raise ApiError(409, "category_exists", message, fields={"name": message}) from error
    except categories.TooManyCategories as error:
        message = f"You can have up to {categories.MAX_CUSTOM} categories of your own."
        raise ApiError(409, "too_many_categories", message) from error
    db.commit()
    return CategoryOut.build(category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404, 409),
)
def delete_category(category_id: str, user: CurrentUser, db: SessionDep) -> None:
    """Delete one of the person's own categories, once no item uses it."""
    category = categories.find_custom(db, user, category_id)
    if category is None:
        raise ApiError(404, "category_not_found", "That category doesn't exist.")
    try:
        categories.delete_custom(db, category)
    except categories.CategoryInUse as error:
        count = f"{error.items} item{'s' if error.items != 1 else ''}"
        message = f"{count} still use this category. Move or delete them first."
        raise ApiError(409, "category_in_use", message) from error
    db.commit()
