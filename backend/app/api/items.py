"""The wardrobe: items, their photos, archiving, and matching sets."""

import uuid
from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query, status
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep, StorageDep
from app.api.errors import ApiError, error_responses
from app.api.fields import Amount, HexColour, IdList, NoteText, ShortText, tidy_text
from app.api.item_views import ItemBrief, Names, PhotoRef, photo_ref
from app.models import Item, ItemImage, User
from app.services import items, wear

router = APIRouter(prefix="/items", tags=["items"])

MAX_TAGS = 15


def _check_purchase_date(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise ValueError("The purchase date can't be in the future.")
    return value


def _tidy_tags(values: Any) -> Any:
    """Tags are short and lower-case; repeats are dropped."""
    if not isinstance(values, list):
        return values
    tidied: list[str] = []
    for value in values:
        if not isinstance(value, str):
            return values  # let validation report it
        tag = " ".join(value.split()).lower()
        if len(tag) > 30:
            raise ValueError("Keep each tag to 30 characters or fewer.")
        if tag and tag not in tidied:
            tidied.append(tag)
    if len(tidied) > MAX_TAGS:
        raise ValueError(f"Use up to {MAX_TAGS} tags.")
    return tidied


Tags = Annotated[list[str] | None, BeforeValidator(_tidy_tags)]


class ItemFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortText = None
    brand: ShortText = None
    size_label: Annotated[str | None, AfterValidator(tidy_text(20))] = None
    color_secondary: str | None = None
    color_hex: HexColour = None
    pattern: str | None = None
    fabric: str | None = None
    fit: str | None = None
    formality: int | None = Field(default=None, ge=1, le=5)
    warmth: int | None = Field(default=None, ge=0, le=5)
    seasons: IdList = None
    occasion_ids: IdList = None
    # Style profile ids ("minimal") and the person's own words.
    style_tags: Tags = None
    # Minor units (paise).
    price: Amount | None = None
    purchased_on: Annotated[date | None, AfterValidator(_check_purchase_date)] = None
    status: str | None = None
    # Null: not washed on a schedule.
    wears_before_wash: int | None = Field(default=None, ge=1, le=30)
    notes: NoteText = None
    # A photo from POST /photos that isn't attached to an item yet.
    photo_id: uuid.UUID | None = None


class ItemCreate(ItemFields):
    """A category and a colour are all an item needs; everything else has a default."""

    category_id: str
    color_primary: str


class ItemUpdate(ItemFields):
    """Only the fields sent are changed. Null clears an optional field, and photo_id null
    removes the photo."""

    category_id: str | None = None
    color_primary: str | None = None


class ItemOut(BaseModel):
    id: uuid.UUID
    category_id: str
    slot: str
    name: str | None
    # The name, or colour and category ("Navy t-shirt") when there is none.
    display_name: str
    brand: str | None
    size_label: str | None
    color_primary: str
    color_secondary: str | None
    color_hex: str | None
    pattern: str
    fabric: str | None
    fit: str | None
    formality: int
    warmth: int
    seasons: list[str]
    occasion_ids: list[str]
    style_tags: list[str]
    price: int | None
    currency: str
    purchased_on: date | None
    status: str
    wears_before_wash: int | None
    wears_since_wash: int
    set_id: uuid.UUID | None
    notes: str | None
    archived: bool
    created_at: datetime
    updated_at: datetime
    photo: PhotoRef | None


class ItemDetailOut(ItemOut):
    # The other items in its matching set.
    set_members: list[ItemBrief]
    # From the wear log.
    wear_count: int
    last_worn_on: date | None


class ItemPage(BaseModel):
    items: list[ItemOut]
    # Pass as `cursor` for the next page; null on the last page.
    next_cursor: str | None
    # How many items match the filters, across all pages.
    total: int


class SetLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: uuid.UUID


_COLUMNS = [
    name for name in ItemOut.model_fields if name not in {"display_name", "archived", "photo"}
]


def _out(item: Item, names: Names, photo: ItemImage | None) -> dict[str, Any]:
    return {
        **{name: getattr(item, name) for name in _COLUMNS},
        "display_name": names.display_name(item),
        "archived": item.archived_at is not None,
        "photo": photo_ref(photo),
    }


def _detail(db: Session, user: User, item: Item) -> ItemDetailOut:
    names = Names(db, user)
    members = items.set_members(db, user, item)
    photos = items.primary_photos(db, [item.id, *(m.id for m in members)])
    worn = wear.item_wear(db, [item.id]).get(item.id)
    return ItemDetailOut.model_validate(
        {
            **_out(item, names, photos.get(item.id)),
            "set_members": [names.brief(m, photos.get(m.id)) for m in members],
            "wear_count": worn.count if worn else 0,
            "last_worn_on": worn.last_worn_on if worn else None,
        }
    )


def _owned(db: Session, user: User, item_id: uuid.UUID) -> Item:
    item = items.find_item(db, user, item_id)
    if item is None:
        # Someone else's item gets the same answer as one that doesn't exist.
        raise ApiError(404, "item_not_found", "That item doesn't exist.")
    return item


def _invalid(error: items.ItemInvalid) -> ApiError:
    return ApiError(422, "invalid_input", "Check the highlighted fields.", fields=error.fields)


ListParam = Annotated[list[str] | None, Query()]


@router.get("", response_model=ItemPage, responses=error_responses(401, 422))
def list_items(
    user: CurrentUser,
    db: SessionDep,
    q: Annotated[str, Query(max_length=100)] = "",
    group: ListParam = None,
    category: ListParam = None,
    slot: ListParam = None,
    color: ListParam = None,
    season: ListParam = None,
    occasion: ListParam = None,
    style: ListParam = None,
    status_: Annotated[list[str] | None, Query(alias="status")] = None,
    archived: bool = False,
    sort: items.Sort = "newest",
    limit: Annotated[int, Query(ge=1, le=60)] = 24,
    cursor: str | None = None,
) -> ItemPage:
    """The wardrobe, filtered and sorted. Within one filter any value matches; across filters,
    all must. An item with no seasons matches every season."""
    filters = items.Filters(
        q=q,
        groups=group or [],
        categories=category or [],
        slots=slot or [],
        colors=color or [],
        seasons=season or [],
        occasions=occasion or [],
        styles=style or [],
        statuses=status_ or [],
        archived=archived,
    )
    try:
        page = items.list_items(db, user, filters, sort, limit, cursor)
    except items.BadCursor as error:
        message = "That page link has expired. Start from the top."
        raise ApiError(422, "bad_cursor", message) from error
    names = Names(db, user)
    photos = items.primary_photos(db, [item.id for item in page.items])
    return ItemPage(
        items=[ItemOut.model_validate(_out(i, names, photos.get(i.id))) for i in page.items],
        next_cursor=page.next_cursor,
        total=page.total,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ItemDetailOut,
    responses=error_responses(401, 403, 422),
)
def create_item(body: ItemCreate, user: CurrentUser, db: SessionDep) -> ItemDetailOut:
    """Add an item. Only the category and colour are needed."""
    try:
        item = items.create_item(db, user, body.model_dump(exclude_unset=True))
    except items.ItemInvalid as error:
        raise _invalid(error) from error
    db.commit()
    return _detail(db, user, item)


@router.get("/{item_id}", response_model=ItemDetailOut, responses=error_responses(401, 404))
def get_item(item_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> ItemDetailOut:
    return _detail(db, user, _owned(db, user, item_id))


@router.patch(
    "/{item_id}", response_model=ItemDetailOut, responses=error_responses(401, 403, 404, 422)
)
def update_item(
    item_id: uuid.UUID, body: ItemUpdate, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> ItemDetailOut:
    item = _owned(db, user, item_id)
    changes = body.model_dump(exclude_unset=True)
    for name in ("seasons", "occasion_ids", "style_tags"):
        if name in changes and changes[name] is None:
            changes[name] = []
    try:
        removed = items.update_item(db, user, item, changes)
    except items.ItemInvalid as error:
        raise _invalid(error) from error
    db.commit()
    storage.delete(removed)
    return _detail(db, user, item)


@router.post(
    "/{item_id}/archive", response_model=ItemDetailOut, responses=error_responses(401, 403, 404)
)
def archive_item(item_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> ItemDetailOut:
    """Hide the item from the wardrobe and suggestions, keeping it and its history."""
    item = _owned(db, user, item_id)
    items.set_archived(db, user, item, archived=True)
    db.commit()
    return _detail(db, user, item)


@router.post(
    "/{item_id}/restore", response_model=ItemDetailOut, responses=error_responses(401, 403, 404)
)
def restore_item(item_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> ItemDetailOut:
    item = _owned(db, user, item_id)
    items.set_archived(db, user, item, archived=False)
    db.commit()
    return _detail(db, user, item)


@router.delete(
    "/{item_id}", status_code=status.HTTP_204_NO_CONTENT, responses=error_responses(401, 403, 404)
)
def delete_item(item_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep) -> None:
    """Delete the item and its photo for good."""
    removed = items.delete_item(db, user, _owned(db, user, item_id))
    db.commit()
    storage.delete(removed)


@router.post(
    "/{item_id}/set", response_model=ItemDetailOut, responses=error_responses(401, 403, 404, 409)
)
def link_set(item_id: uuid.UUID, body: SetLink, user: CurrentUser, db: SessionDep) -> ItemDetailOut:
    """Make two items a matching set, such as a suit's jacket and trousers."""
    item = _owned(db, user, item_id)
    other = _owned(db, user, body.item_id)
    if other.id == item.id:
        raise ApiError(409, "same_item", "Choose a different item to pair it with.")
    try:
        items.link_set(db, user, item, other)
    except items.SetTooLarge as error:
        message = f"A matching set can have up to {items.MAX_SET_SIZE} items."
        raise ApiError(409, "set_too_large", message) from error
    db.commit()
    return _detail(db, user, item)


@router.delete(
    "/{item_id}/set", response_model=ItemDetailOut, responses=error_responses(401, 403, 404)
)
def unlink_set(item_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> ItemDetailOut:
    """Take the item out of its matching set."""
    item = _owned(db, user, item_id)
    items.unlink_set(db, user, item)
    db.commit()
    return _detail(db, user, item)
