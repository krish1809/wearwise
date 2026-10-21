"""Everything a person has stored, as one zip file: every row of theirs, and every photo.

Which tables hold a person's data is read from the schema, not listed by hand: a table with a
`user_id`, or one that hangs off such a table and is deleted with it. So a table added later is
exported (and deleted with the account) without anyone remembering to add it here; a test
checks that every table is either the person's or in SHARED.
"""

import json
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import IO, Any

from sqlalchemy import Table, select
from sqlalchemy.orm import Session

from app.adapters.storage import Storage
from app.models import Base, ItemImage, User
from app.services import checkpoints

# Tables that hold nothing of any one person's: reference data, shared caches, the
# rate-limit counters (which only count, and expire within the hour), the agents' run log
# (counts, queries, and sources, never who a digest went to), and the trends the Trend Scout
# found on the web.
SHARED = {
    "agent_runs",
    "app_meta",
    "archetypes",
    "catalog_products",
    "category_groups",
    "color_families",
    "error_events",
    "guide_entries",
    "link_previews",
    "occasions",
    "outfit_templates",
    "rate_limit_hits",
    "style_profiles",
    "trend_sources",
    "trends",
    "vocabulary_terms",
    "weather_forecasts",
}
# Kept out of the export: login sessions and links sent by email (only hashes of their tokens),
# and the password hash.
LEFT_OUT_TABLES = {"email_tokens", "sessions"}
# Not in the models at all: the agents' checkpoint tables, which their library owns. They hold
# only runs that haven't finished (the conversation itself is in chat_messages), so they're left
# out of the export, and deleted with the account by thread id (app/services/checkpoints.py; D59).
RUN_STATE = set(checkpoints.TABLES)
LEFT_OUT_COLUMNS = {"users": {"password_hash"}}
# Spill to disk past this, so a large wardrobe doesn't sit in memory.
IN_MEMORY = 16 * 1024 * 1024

README = """WearWise: everything stored for your account, exported {when}.

data.json holds every row that belongs to you, one list per table, with the same column names
the app uses. Ids link rows together: an outfit's pieces are in outfit_items, by outfit_id and
item_id. Money is in paise (or the currency's smallest unit). Times are UTC.

photos/ holds each photo at the size WearWise stores (up to 1600 px, WebP), named by its id
in item_images. Your password and login sessions are not included.
"""


@dataclass(frozen=True)
class Owned:
    """A table holding a person's rows, and how to find them: by `user_id`, or through the
    parent table its rows are deleted with."""

    table: Table
    parent: str | None = None
    via: str | None = None


def owned_tables() -> list[Owned]:
    """Every table with a person's data, parents before children."""
    found: dict[str, Owned] = {}
    for table in Base.metadata.sorted_tables:
        if table.name == "users":
            continue
        if "user_id" in table.c and any(
            fk.column.table.name == "users" for fk in table.c.user_id.foreign_keys
        ):
            found[table.name] = Owned(table)
            continue
        for fk in table.foreign_keys:
            if fk.column.table.name in found and fk.ondelete == "CASCADE":
                found[table.name] = Owned(table, fk.column.table.name, fk.parent.name)
                break
    return list(found.values())


def _condition(db: Session, owned: dict[str, Owned], entry: Owned, user_id: uuid.UUID) -> Any:
    """Which of the table's rows are the person's."""
    if entry.parent is None or entry.via is None:
        return entry.table.c.user_id == user_id
    parent = owned[entry.parent]
    parents = select(parent.table.c.id).where(_condition(db, owned, parent, user_id))
    return entry.table.c[entry.via].in_(parents)


def rows_for(db: Session, user: User) -> dict[str, list[dict[str, Any]]]:
    """Every row of the person's, by table."""
    owned = {entry.table.name: entry for entry in owned_tables()}
    users = Base.metadata.tables["users"]
    data = {"users": _plain(db, users, users.c.id == user.id)}
    for name, entry in owned.items():
        if name not in LEFT_OUT_TABLES:
            data[name] = _plain(db, entry.table, _condition(db, owned, entry, user.id))
    return data


def _plain(db: Session, table: Table, condition: Any) -> list[dict[str, Any]]:
    left_out = LEFT_OUT_COLUMNS.get(table.name, set())
    columns = [column for column in table.c if column.name not in left_out]
    order = [table.c.created_at] if "created_at" in table.c else []
    query = select(*columns).where(condition).order_by(*order, *table.primary_key.columns)
    return [
        {key: _json_value(value) for key, value in row.items()}
        for row in db.execute(query).mappings()
    ]


def _json_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_json_value(v) for v in value]
    return value


def build(db: Session, storage: Storage, user: User) -> IO[bytes]:
    """The zip, written to a temporary file (in memory while it's small), read from the
    start. The caller closes it."""
    data = rows_for(db, user)
    images = list(
        db.scalars(select(ItemImage).where(ItemImage.user_id == user.id).order_by(ItemImage.id))
    )
    now = datetime.now(UTC)
    out = tempfile.SpooledTemporaryFile(max_size=IN_MEMORY)  # noqa: SIM115 (the caller closes it)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", README.format(when=now.strftime("%Y-%m-%d %H:%M UTC")))
        archive.writestr(
            "data.json",
            json.dumps({"exported_at": now.isoformat(), "tables": data}, indent=1),
        )
        for image in images:
            photo = storage.get(image.storage_key)
            if photo is not None:
                # WebP is already compressed; storing it as it is saves time.
                archive.writestr(f"photos/{image.id}.webp", photo, zipfile.ZIP_STORED)
    out.seek(0)
    return out
