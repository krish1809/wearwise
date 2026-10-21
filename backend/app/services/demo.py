"""A demo wardrobe made from the generic staples in seed/archetypes.json, with the profile in
seed/demo.json.

Two ways in: "Try the demo" gives each visitor a fresh account of their own, deleted a day
later (D52); and the demo script fills a named demo account. Only demo accounts are touched:
they're created as demos, and any account that isn't one is refused. The items have no photos
(the app shows their colour instead) and no prices, because the staples carry none.
"""

import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Item, ItemImage, User
from app.services import auth, items, profile
from app.services.reference_seed import SEED_DIR

Section = Literal["menswear", "womenswear", "both"]

# A visitor's demo lasts this long, and at most this many run at once (the oldest go first).
LIFETIME = timedelta(days=1)
MAX_LIVE = 300
# Addresses that can't receive mail (".invalid" is reserved for exactly this).
DOMAIN = "demo.wearwise.invalid"


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
    """Create or reset a named demo account's wardrobe (the demo script). The caller commits."""
    email = auth.normalize_email(email)
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
    count = _fill(db, user, section, seed_dir)
    return DemoLoaded(items=count, password=password, stale_keys=keys)


def start_demo(
    db: Session, section: Section, now: datetime | None = None, seed_dir: Path = SEED_DIR
) -> tuple[User, list[str]]:
    """A fresh demo account for one visitor, with an address nobody can log in with and a
    password nobody knows: the session started for it is the only way in. Makes room first
    (expired demos, and the oldest when too many are running). Returns the account and photo
    files to delete once committed; the caller commits."""
    now = now or datetime.now(UTC)
    _, keys = remove_expired(db, now)
    live = db.scalar(select(func.count()).where(User.is_demo)) or 0
    if live >= MAX_LIVE:
        oldest = db.scalars(
            select(User.id).where(User.is_demo).order_by(User.created_at).limit(live - MAX_LIVE + 1)
        )
        keys += _remove(db, list(oldest))
    user = auth.register(
        db,
        email=f"visitor-{secrets.token_hex(8)}@{DOMAIN}",
        password=secrets.token_urlsafe(32),
        name=None,
    )
    user.is_demo = True
    _fill(db, user, section, seed_dir)
    return user, keys


def remove_expired(db: Session, now: datetime, limit: int = 100) -> tuple[int, list[str]]:
    """Delete visitors' demo accounts older than a day, a batch at a time. Named demo accounts
    (the demo script's) stay. Returns how many went, and photo files to delete once
    committed."""
    expired = list(
        db.scalars(
            select(User.id)
            .where(
                User.is_demo, User.email.endswith(f"@{DOMAIN}"), User.created_at < now - LIFETIME
            )
            .order_by(User.created_at)
            .limit(limit)
        )
    )
    return len(expired), _remove(db, expired)


def _remove(db: Session, user_ids: list[uuid.UUID]) -> list[str]:
    if not user_ids:
        return []
    images = db.scalars(select(ItemImage).where(ItemImage.user_id.in_(user_ids)))
    keys = [key for image in images for key in (image.storage_key, image.thumb_key)]
    # Everything of theirs goes with them (ON DELETE CASCADE; D50).
    db.execute(delete(User).where(User.id.in_(user_ids), User.is_demo))
    db.flush()
    return keys


def _fill(db: Session, user: User, section: Section, seed_dir: Path) -> int:
    staples = json.loads((seed_dir / "archetypes.json").read_text())["archetypes"]
    if section != "both":
        staples = [s for s in staples if section in s["sections"]]
    setup = json.loads((seed_dir / "demo.json").read_text())
    sections = ["menswear", "womenswear"] if section == "both" else [section]
    profile.update_profile(
        db,
        user,
        {
            "sections": sections,
            "occasion_ids": setup["occasion_ids"],
            "weekday_occasions": setup["weekday_occasions"],
            "style_profile_ids": setup["style_profile_ids"],
            "city": setup["city"],
            "latitude": setup["latitude"],
            "longitude": setup["longitude"],
        },
    )
    profile.finish_onboarding(db, user, skipped=False)
    # Made last to first, so "newest first" opens on the first staples (clothes, not toiletries).
    for staple in reversed(staples):
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
    return len(staples)
