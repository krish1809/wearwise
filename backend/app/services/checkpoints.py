"""The agents' checkpoint tables, seen from the rest of the app (D59).

LangGraph's Postgres checkpointer keeps a run in progress in four tables of its own, which it
creates and versions itself (app/agents/checkpoint.py), so they aren't in the models and no
migration makes them. They have no `user_id`, so the rule that makes deleting an account
complete (every table points at its person) can't see them. Instead, every thread id says whose
it is, and this module deletes by thread id: a person's when their account goes, and anyone's
left behind after a day.

Plain SQL in the caller's transaction, so services can use it without importing the agents.
"""

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import ChatThread

TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations")
# The tables holding runs; checkpoint_migrations only records the tables' version.
THREAD_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")
# A finished run deletes its own checkpoints; anything older than this was left by a run that
# died, or a stylist turn nobody came back to confirm.
KEPT_FOR = timedelta(days=1)


def chat_thread(thread_id: uuid.UUID) -> str:
    return f"chat:{thread_id}"


def digest_thread(user_id: uuid.UUID, week: str) -> str:
    return f"digest:{user_id}:{week}"


def scout_thread(run_id: uuid.UUID) -> str:
    return f"scout:{run_id}"


def include_name(name: str | None, type_: str, parent_names: Mapping[str, str | None]) -> bool:
    """For Alembic: leave the checkpointer's tables alone, or autogenerate would drop them."""
    return not (type_ == "table" and name in TABLES)


def _present(db: Session) -> bool:
    # They exist once scripts/agent_setup.py has run, which every deploy does after migrating.
    return bool(db.scalar(text("SELECT to_regclass('checkpoints') IS NOT NULL")))


def forget(db: Session, thread_ids: Sequence[str] = (), prefixes: Sequence[str] = ()) -> None:
    """Delete these threads' checkpoints, and every thread starting with one of the prefixes."""
    if not (thread_ids or prefixes) or not _present(db):
        return
    patterns = [prefix + "%" for prefix in prefixes]
    for table in THREAD_TABLES:
        db.execute(
            text(f"DELETE FROM {table} WHERE thread_id = ANY(:ids) OR thread_id LIKE ANY(:like)"),
            {"ids": list(thread_ids), "like": patterns},
        )


def forget_people(db: Session, user_ids: Sequence[uuid.UUID]) -> None:
    """Delete everything the checkpointer holds for these people: their chat threads' runs and
    their digests'. Call it before deleting the accounts, while their chat threads exist."""
    if not user_ids:
        return
    chats = db.scalars(select(ChatThread.id).where(ChatThread.user_id.in_(user_ids)))
    forget(
        db,
        thread_ids=[chat_thread(thread) for thread in chats],
        prefixes=[f"digest:{user_id}:" for user_id in user_ids],
    )


def remove_stale(db: Session, now: datetime) -> int:
    """Delete threads whose latest checkpoint is older than KEPT_FOR. Returns how many."""
    if not _present(db):
        return 0
    stale = list(
        db.scalars(
            text(
                "SELECT thread_id FROM checkpoints GROUP BY thread_id "
                "HAVING max((checkpoint->>'ts')::timestamptz) < :cutoff"
            ),
            {"cutoff": now - KEPT_FOR},
        )
    )
    forget(db, thread_ids=stale)
    return len(stale)
