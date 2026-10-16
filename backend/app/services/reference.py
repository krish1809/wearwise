"""Read the reference lists, and check ids against them."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CategoryGroup, ColorFamily, Occasion, StyleProfile, VocabularyTerm


def ordered[T: (CategoryGroup, ColorFamily, Occasion, StyleProfile)](
    db: Session, model: type[T]
) -> list[T]:
    return list(db.scalars(select(model).order_by(model.position)))


def terms(db: Session, kind: str) -> list[VocabularyTerm]:
    query = select(VocabularyTerm).where(VocabularyTerm.kind == kind)
    return list(db.scalars(query.order_by(VocabularyTerm.position)))


def known_ids(
    db: Session, model: type[CategoryGroup | ColorFamily | Occasion | StyleProfile]
) -> set[str]:
    return set(db.scalars(select(model.id)))


def known_terms(db: Session, kind: str) -> set[str]:
    return set(db.scalars(select(VocabularyTerm.id).where(VocabularyTerm.kind == kind)))
