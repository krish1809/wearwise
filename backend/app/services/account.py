"""Deleting an account and everything that belongs to it."""

from sqlalchemy.orm import Session

from app.models.user import User


def delete_account(db: Session, user: User) -> None:
    """Remove the person and all their data.

    Every milestone that stores user data extends this function. Today that is the user row,
    their sessions, profile, and brand notes; the database removes the rest with the user
    (ON DELETE CASCADE). From M3, stored photos must be deleted here too.
    """
    db.delete(user)
    db.flush()
