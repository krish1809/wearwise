"""Deleting an account and everything that belongs to it."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.storage import Storage
from app.models import ItemImage, User


def delete_account(db: Session, storage: Storage, user: User) -> None:
    """Remove the person and all their data, then their stored photos.

    Every milestone that stores user data extends this function. The database removes every
    row that belongs to the user with it (ON DELETE CASCADE): sessions, profile, brand notes,
    custom categories, items, photo records, outfits, the wear log, and suggestions with their
    feedback. The photo files are deleted after the commit, so a storage failure can't leave
    the account half deleted.
    """
    images = db.scalars(select(ItemImage).where(ItemImage.user_id == user.id))
    keys = [key for image in images for key in (image.storage_key, image.thumb_key)]
    db.delete(user)
    db.commit()
    storage.delete(keys)
