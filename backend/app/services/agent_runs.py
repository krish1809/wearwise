"""The agents' run log (docs/AGENTS.md, section 6): a row per run, and at most one running row
per kind, so a scheduled job and one started by hand can't overlap (D56). A row left running
for longer than any run takes is from a job that died without saying so; it lapses, and the
next run goes ahead.
"""

from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AgentRun

LAPSE = timedelta(hours=2)
# The most errors one run keeps, each shortened, so a run that fails for everyone stays small.
MOST_ERRORS = 20
ERROR_CHARACTERS = 500


class AlreadyRunning(Exception):
    """Another run of the same kind holds the running row."""


def start(db: Session, kind: str, trigger: str, now: datetime) -> AgentRun:
    """Take the kind's running row. Raises AlreadyRunning; the caller commits."""
    db.execute(
        update(AgentRun)
        .where(
            AgentRun.kind == kind,
            AgentRun.status == "running",
            AgentRun.started_at < now - LAPSE,
        )
        .values(status="failed", finished_at=now, stopped_by="lapsed")
    )
    run = AgentRun(kind=kind, trigger=trigger, status="running", started_at=now)
    try:
        with db.begin_nested():
            db.add(run)
    except IntegrityError as error:
        raise AlreadyRunning(kind) from error
    return run


def note_error(run: AgentRun, message: str) -> None:
    if len(run.errors) < MOST_ERRORS:
        run.errors = [*run.errors, message[:ERROR_CHARACTERS]]


def finish(run: AgentRun, status: str, now: datetime, stopped_by: str | None = None) -> AgentRun:
    """Record how the run ended: done, stopped (with the limit that stopped it), or failed.
    The caller commits."""
    run.status = status
    run.finished_at = now
    run.stopped_by = stopped_by
    return run


def latest(db: Session, kind: str, limit: int = 20) -> list[AgentRun]:
    return list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.kind == kind)
            .order_by(AgentRun.started_at.desc())
            .limit(limit)
        )
    )
