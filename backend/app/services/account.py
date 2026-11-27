"""Deleting an account and everything that belongs to it."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.storage import Storage
from app.models import ItemImage, User
from app.services import checkpoints


def delete_account(db: Session, storage: Storage, user: User) -> None:
    """Remove the person and all their data, then their stored photos.

    The database removes every row that belongs to the user with it: every table with a
    `user_id` points at the user with ON DELETE CASCADE, and every table hanging off one of
    those cascades from it (tests/test_privacy.py checks both, for every table). The photo
    files are deleted after the commit, so a storage failure can't leave the account half
    deleted. The agents' checkpoints have no `user_id`, so they're deleted by thread first
    (D59).
    """
    images = db.scalars(select(ItemImage).where(ItemImage.user_id == user.id))
    keys = [key for image in images for key in (image.storage_key, image.thumb_key)]
    checkpoints.forget_people(db, [user.id])
    db.delete(user)
    db.commit()
    storage.delete(keys)
