"""The weekly email, run daily on a schedule or by hand (docs/AGENTS.md, sections 5 and 6):

  uv run python -m app.jobs.weekly_digest

Each run emails everyone whose day it is, and anyone whose day was in the last two days whose
email hasn't gone (a dropped or late run, or one the daily cap held back), up to
DIGEST_BATCH_CAP; anyone left over is the next run's. One person's failure is recorded and the
rest go on. The run log and these logs, which are public on GitHub, hold counts and error types
only: never who.
"""

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.ai import Usage
from app.adapters.email import get_email_sender
from app.agents import checkpoint
from app.agents import digest as weekly
from app.agents.model import get_chat_model
from app.agents.tracing import traced
from app.core.config import get_settings
from app.jobs.runner import Ended, now, run_job
from app.models import AgentRun, Digest, Profile, User
from app.services import agent_runs, ai_usage, digests, subscriptions

log = logging.getLogger(__name__)

INDIA = ZoneInfo("Asia/Kolkata")
CATCH_UP_DAYS = 2


@dataclass(frozen=True)
class Due:
    user: User
    # The ISO week of the person's email day.
    week: str


def due(db: Session, when: datetime) -> list[Due]:
    """Everyone whose email is due: their day is today in India, or was in the last two days
    and that week's email hasn't gone."""
    today = when.astimezone(INDIA).date()
    found: list[Due] = []
    for user in subscriptions.subscribed(db):
        profile = db.scalars(select(Profile).where(Profile.user_id == user.id)).one()
        late = (today.weekday() - profile.digest_weekday) % 7
        if late > CATCH_UP_DAYS:
            continue
        week = digests.week_of(today - timedelta(days=late))
        sent = db.scalar(
            select(Digest.id).where(
                Digest.user_id == user.id, Digest.week == week, Digest.status == "sent"
            )
        )
        if sent is None:
            found.append(Due(user, week))
    return found


def work(db: Session, run: AgentRun) -> Ended:
    when = now()
    people = due(db, when)
    cap = get_settings().digest_batch_cap
    model = get_chat_model()
    sender = get_email_sender()
    counts: Counter[str] = Counter()
    with checkpoint.saver() as saver:
        for person in people[:cap]:
            try:
                with traced("weekly_digest"):
                    outcome = weekly.run(db, person.user, model, sender, saver, when, person.week)
            except Exception as error:
                db.rollback()
                counts["failed"] += 1
                # The type only: a message could carry an address into the public logs.
                agent_runs.note_error(run, f"one email: {type(error).__name__}")
                log.warning("A weekly email failed: %s", type(error).__name__)
                continue
            counts[outcome.email if outcome.email != "not_sent" else outcome.status] += 1
            counts[f"wording_{outcome.wording}"] += outcome.email == "sent"
            run.tokens_in += outcome.tokens_in
            run.tokens_out += outcome.tokens_out
            # For the run log; the daily cap already counted it against the person.
            run.cost_micro_usd += ai_usage.cost_micro_usd(
                Usage(outcome.tokens_in, outcome.tokens_out)
            )
    over = max(0, len(people) - cap)
    run.steps = {"send": {"due": len(people), "over_cap": over, **counts}}
    db.commit()
    return Ended("stopped", "batch_cap") if over else Ended()


def main() -> None:
    raise SystemExit(run_job("weekly_digest", work))


if __name__ == "__main__":
    main()
