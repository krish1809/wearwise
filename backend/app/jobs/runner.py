"""What every scheduled job does around its own work: set up the checkpoint tables, take its
kind's running row (or step aside if another run has it), do the work, record how it ended, and
report to the owner. A failure is recorded, reported, and gives a non-zero exit, so GitHub shows
the run as failed.
"""

import logging
import os
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents import checkpoint
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.core.logs import configure_logging
from app.models import AgentRun
from app.services import agent_runs

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Ended:
    """How a job's work ended: done, or stopped by one of its limits."""

    status: str = "done"
    stopped_by: str | None = None


Work = Callable[[Session, AgentRun], Ended]
# Told how the run ended, after it's recorded; its own failure changes nothing about the run.
Report = Callable[[Session, AgentRun], None]
Sessions = Callable[[], AbstractContextManager[Session]]


def trigger() -> str:
    """schedule when GitHub started the job on its timetable; manual otherwise."""
    return "schedule" if os.environ.get("GITHUB_EVENT_NAME") == "schedule" else "manual"


def now() -> datetime:
    return datetime.now(UTC)


def run_job(
    kind: str,
    work: Work,
    sessions: Sessions | None = None,
    prepare: bool = True,
    report: Report | None = None,
) -> int:
    """Run one job; returns the process's exit code."""
    configure_logging(get_settings().is_production)
    if prepare:
        checkpoint.setup()
    open_session = sessions or get_sessionmaker()
    with open_session() as db:
        try:
            run = agent_runs.start(db, kind, trigger(), now())
            db.commit()
        except agent_runs.AlreadyRunning:
            log.info("Another %s run is in progress; this one stepped aside.", kind)
            return 0
        code = 0
        try:
            ended = work(db, run)
            agent_runs.finish(run, ended.status, now(), ended.stopped_by)
        except Exception as error:
            log.exception("The %s run failed", kind)
            db.rollback()
            agent_runs.note_error(run, f"{type(error).__name__}: {error}")
            agent_runs.finish(run, "failed", now())
            code = 1
        db.commit()
        log.info("The %s run ended: %s", kind, run.status)
        if report is not None:
            try:
                report(db, run)
                db.commit()
            except Exception:
                log.exception("The %s run's report couldn't be sent", kind)
                db.rollback()
    return code
