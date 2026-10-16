"""A demo wardrobe made from the generic staples in seed/archetypes.json.

Only demo accounts are touched: the account is created as one, and any account that isn't a
demo is refused. The items have no photos (the app shows their colour instead) and no prices,
because the staples carry none.
"""

import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Item, ItemImage, User
from app.services import auth, items, profile
from app.services.reference_seed import SEED_DIR

Section = Literal["menswear", "womenswear", "both"]


class NotADemoAccount(Exception):
    pass


@dataclass(frozen=True)
class DemoLoaded:
    items: int
    # Set only when the account was created now; shown once, never stored in plain text.
    password: str | None
    # Photo files from the previous demo wardrobe, to delete once committed.
    stale_keys: list[str]


def load_demo(
    db: Session, email: str, section: Section = "both", seed_dir: Path = SEED_DIR
) -> DemoLoaded:
    """Create or reset the demo account's wardrobe. The caller commits."""
    email = auth.normalize_email(email)
    staples = json.loads((seed_dir / "archetypes.json").read_text())["archetypes"]
    if section != "both":
        staples = [s for s in staples if section in s["sections"]]

    user = db.scalar(select(User).where(User.email == email))
    password = None
    if user is None:
        password = secrets.token_urlsafe(12)
        user = auth.register(db, email=email, password=password, name="Demo")
        user.is_demo = True
    elif not user.is_demo:
        raise NotADemoAccount(email)

    # Start from an empty wardrobe each time.
    images = db.scalars(select(ItemImage).where(ItemImage.user_id == user.id))
    keys = [key for image in images for key in (image.storage_key, image.thumb_key)]
    db.execute(delete(Item).where(Item.user_id == user.id))
    db.execute(delete(ItemImage).where(ItemImage.user_id == user.id))

    sections = ["menswear", "womenswear"] if section == "both" else [section]
    profile.update_profile(db, user, {"sections": sections})
    profile.finish_onboarding(db, user, skipped=False)

    for staple in staples:
        items.create_item(
            db,
            user,
            {
                "category_id": staple["category"],
                "color_primary": staple["color"],
                "name": staple["name"],
                "pattern": staple["pattern"],
                "fabric": staple["fabric"],
                "formality": staple["formality"],
                "warmth": staple["warmth"],
                "seasons": staple["seasons"],
                "style_tags": staple["styles"],
                "attrs": staple.get("attrs") or {},
            },
        )
    db.flush()
    return DemoLoaded(items=len(staples), password=password, stale_keys=keys)
