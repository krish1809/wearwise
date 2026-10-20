"""Categories: the seeded ones everyone sees, and each person's own."""

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Candidate, Category, Item, User

# Far more than anyone needs; keeps the category list one small response.
MAX_CUSTOM = 100


class CategoryExists(Exception):
    pass


class TooManyCategories(Exception):
    pass


class CategoryInUse(Exception):
    def __init__(self, items: int, candidates: int = 0) -> None:
        super().__init__(f"{items} items and {candidates} candidates use this category")
        self.items = items
        self.candidates = candidates


def visible_to(user: User) -> Any:
    """The condition for categories this person can see and use."""
    return or_(Category.user_id.is_(None), Category.user_id == user.id)


def list_categories(db: Session, user: User) -> list[Category]:
    """Seeded categories in the seed's order, then the person's own, A to Z."""
    query = select(Category).where(visible_to(user))
    query = query.order_by(
        Category.user_id.is_not(None), Category.position, func.lower(Category.name)
    )
    return list(db.scalars(query))


def find_category(db: Session, user: User, category_id: str) -> Category | None:
    query = select(Category).where(Category.id == category_id, visible_to(user))
    return db.scalar(query)


def create_custom(db: Session, user: User, fields: dict[str, Any]) -> Category:
    count = db.scalar(select(func.count()).where(Category.user_id == user.id)) or 0
    if count >= MAX_CUSTOM:
        raise TooManyCategories
    formality = fields.pop("formality_default") or 3
    if fields.get("warmth") is None:
        fields["warmth"] = 1
    position = (db.scalar(select(func.max(Category.position))) or 0) + 1
    category = Category(
        id=f"custom_{uuid.uuid7().hex}",
        user_id=user.id,
        # Shown whichever sections the person shops.
        sections=[],
        formality_default=formality,
        formality_min=max(1, formality - 1),
        formality_max=min(5, formality + 1),
        position=position,
        **fields,
    )
    try:
        with db.begin_nested():
            db.add(category)
            db.flush()
    except IntegrityError as error:
        raise CategoryExists from error
    return category


def find_custom(db: Session, user: User, category_id: str) -> Category | None:
    """One of the person's own categories; seeded ones can't be changed."""
    query = select(Category).where(Category.id == category_id, Category.user_id == user.id)
    return db.scalar(query)


def delete_custom(db: Session, category: Category) -> None:
    items = db.scalar(select(func.count()).where(Item.category_id == category.id)) or 0
    wanted = db.scalar(select(func.count()).where(Candidate.category_id == category.id)) or 0
    if items or wanted:
        raise CategoryInUse(items, wanted)
    db.delete(category)
    db.flush()
