"""The Trend Scout, run on a schedule or by hand (docs/AGENTS.md, section 4):

  uv run python -m app.jobs.trend_scout

It needs a search provider (SEARCH_PROVIDER) and the model (AI_PROVIDER). With the model off it
stops before searching, so no credits are spent on pages nothing could read. Every run ends
with a report to the owner (ADMIN_EMAILS), by email.
"""

from sqlalchemy.orm import Session

from app.adapters.email import get_email_sender
from app.adapters.search import get_web_search
from app.agents import checkpoint, trend_scout
from app.agents.model import get_chat_model
from app.jobs.runner import Ended, now, run_job
from app.models import AgentRun
from app.services import run_report


class SearchOff(RuntimeError):
    pass


def work(db: Session, run: AgentRun) -> Ended:
    web = get_web_search()
    if web is None:
        raise SearchOff(
            "SEARCH_PROVIDER is off: set it to tavily, with SEARCH_API_KEY, to run the Trend Scout"
        )
    with checkpoint.saver() as saver:
        outcome = trend_scout.run(db, run, web, get_chat_model(), saver, now())
    if outcome.stopped_by:
        return Ended("stopped", outcome.stopped_by)
    return Ended()


def report(db: Session, run: AgentRun) -> None:
    """The owner's run report: what it searched for, read, kept, dropped, and spent."""
    run_report.send_scout_report(db, run, get_email_sender(), now())


def main() -> None:
    raise SystemExit(run_job("trend_scout", work, report=report))


if __name__ == "__main__":
    main()
