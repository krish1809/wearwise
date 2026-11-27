"""LangGraph's Postgres checkpointer (D59): where a run in progress is kept, so it can stop and
resume.

The library creates and versions its own tables, building indexes concurrently, which can't
happen inside a migration's transaction. So `setup()` runs as its own step after the migrations
(scripts/agent_setup.py, on every deploy and before every job), and Alembic leaves the tables
alone (app.services.checkpoints.include_name).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection, errors
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings


def plain_url(url: str) -> str:
    """psycopg's form of a database address: the settings hold SQLAlchemy's, which names the
    driver."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def setup(url: str | None = None) -> None:
    """Create the tables, or bring them up to the library's version. Safe to run any time.
    Prefers the direct connection, as migrations do."""
    settings = get_settings()
    address = plain_url(url or settings.migration_database_url or settings.database_url)
    try:
        _setup(address)
    except errors.UniqueViolation:
        # Another process (a deploy, a job) was setting up at the same moment and recorded
        # the same version first; the second pass finds it done.
        _setup(address)


def _setup(address: str) -> None:
    # from_conn_string connects with autocommit and without prepared statements, which the
    # concurrent indexes and Neon's connection pooler both need.
    with PostgresSaver.from_conn_string(address) as saver:
        saver.setup()


@contextmanager
def saver(url: str | None = None) -> Iterator[PostgresSaver]:
    """A checkpointer on its own connection, for one job."""
    with PostgresSaver.from_conn_string(plain_url(url or get_settings().database_url)) as found:
        yield found


@lru_cache
def shared() -> PostgresSaver:
    """The API's checkpointer, for the stylist's turns that wait for a confirmation: a small
    pool, opened on first use, with the settings the library needs."""
    pool: ConnectionPool[Connection[DictRow]] = ConnectionPool(
        plain_url(get_settings().database_url),
        min_size=0,
        max_size=4,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    return PostgresSaver(pool)


def get_checkpointer() -> PostgresSaver:
    """For the API's routes; tests swap in their own."""
    return shared()


def close_shared() -> None:
    """Close the API's pool, if it was opened: on shutdown, so its threads end cleanly."""
    if shared.cache_info().currsize:
        pool = shared().conn
        shared.cache_clear()
        pool.close()
