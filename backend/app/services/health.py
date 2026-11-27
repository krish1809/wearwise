"""Checks that the database answers and has been migrated."""

import logging

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.app_meta import AppMeta

logger = logging.getLogger(__name__)


def database_is_ready(session: Session) -> bool:
    """Read the row the first migration wrote. Missing row or failed query means not ready."""
    try:
        value = session.scalar(select(AppMeta.value).where(AppMeta.key == "app"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return False
    if value is None:
        logger.error("app_meta has no 'app' row; have the migrations run?")
        return False
    return True


def migration_revision(session: Session) -> str | None:
    """The Alembic revision the database is at, so a deploy check can compare it with the code.

    Alembic keeps one row per head; more than one only happens mid-merge, so they are joined.
    None when the table can't be read.
    """
    try:
        rows = session.scalars(text("SELECT version_num FROM alembic_version")).all()
    except SQLAlchemyError:
        logger.exception("Reading the migration revision failed")
        return None
    return ",".join(sorted(rows)) or None
