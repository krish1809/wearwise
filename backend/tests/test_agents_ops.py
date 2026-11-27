"""Running the agents (docs/AGENTS.md, sections 4, 6, and 7): the owner's approval page and run
log, the rules every email goes through, the owner's run report, and the settings the jobs run
with."""

import email.message
import json
import urllib.error
import urllib.request
import uuid
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import select
from sqlalchemy.orm import Session
from trend_support import SITES, search
from wardrobe_support import add_item

from app.adapters import storage
from app.adapters.email import Email, EmailUnavailable, FakeEmail, ResendEmail
from app.agents import trend_scout
from app.agents.fake import ScriptedChatModel
from app.core.config import ConfigError, Settings, get_settings, load_settings
from app.jobs import runner
from app.jobs.runner import Ended
from app.models import AgentRun, EmailEvent, Trend, TrendSource
from app.services import agent_runs, mail, run_report, trends
from app.services.housekeeping import tidy

NOW = datetime.now(UTC)
TRENDS = "/api/v1/admin/trends"
RUNS = "/api/v1/admin/runs"


def as_owner(app: FastAPI, email: str) -> None:
    settings: Settings = get_settings().model_copy(update={"admin_emails": email})
    app.dependency_overrides[get_settings] = lambda: settings


def a_trend(db: Session, name: str = "Linen co-ord sets", status: str = "pending") -> Trend:
    trend = Trend(
        name=name,
        name_key=trends.name_key(name),
        summary="Matching linen shirts and trousers.",
        why_now="Warm afternoons.",
        category_ids=["co_ord_set"],
        color_families=["sage"],
        fabrics=["linen"],
        sections=["menswear"],
        status=status,
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    db.add(trend)
    db.flush()
    db.add(
        TrendSource(
            trend_id=trend.id,
            url="https://style-one.example/linen",
            domain="style-one.example",
            title="Linen co-ords for easy days",
            published_on=NOW.date() - timedelta(days=3),
            quote="linen co-ord sets in sage and beige",
        )
    )
    db.flush()
    return trend


def test_only_the_owner_sees_and_decides_trends_and_runs(
    app: FastAPI, db: Session, sam: TestClient, ana: TestClient
) -> None:
    as_owner(app, "sam@example.com")
    trend = a_trend(db)

    theirs = [
        ana.get(TRENDS).status_code,
        ana.patch(f"{TRENDS}/{trend.id}", json={"status": "approved"}).status_code,
        ana.get(RUNS).status_code,
    ]
    mine = sam.get(TRENDS)

    # The same answer as a page that doesn't exist, and nothing changed.
    assert theirs == [404, 404, 404]
    db.refresh(trend)
    assert trend.status == "pending"
    assert mine.status_code == 200


def test_the_owner_sees_pending_trends_with_their_sources_and_names(
    app: FastAPI, db: Session, sam: TestClient
) -> None:
    as_owner(app, "sam@example.com")
    a_trend(db)
    a_trend(db, "Velvet blazers", status="approved")

    found = sam.get(TRENDS).json()

    [trend] = found["trends"]
    assert trend["name"] == "Linen co-ord sets"
    assert trend["categories"] == [{"id": "co_ord_set", "name": "Co-ord set (worn as one)"}]
    assert trend["colors"][0]["id"] == "sage" and trend["colors"][0]["hex"]
    assert trend["sources"] == [
        {
            "url": "https://style-one.example/linen",
            "domain": "style-one.example",
            "title": "Linen co-ords for easy days",
            "published_on": (NOW.date() - timedelta(days=3)).isoformat(),
            "quote": "linen co-ord sets in sage and beige",
        }
    ]
    assert found["counts"] == {"pending": 1, "approved": 1, "rejected": 0, "expired": 0}
    assert [t["name"] for t in sam.get(TRENDS, params={"status": "approved"}).json()["trends"]] == [
        "Velvet blazers"
    ]


def test_the_owner_approves_rejects_and_undoes(app: FastAPI, db: Session, sam: TestClient) -> None:
    as_owner(app, "sam@example.com")
    trend = a_trend(db)

    approved = sam.patch(f"{TRENDS}/{trend.id}", json={"status": "approved"})
    undone = sam.patch(f"{TRENDS}/{trend.id}", json={"status": "pending"})
    rejected = sam.patch(f"{TRENDS}/{trend.id}", json={"status": "rejected"})
    expired = sam.patch(f"{TRENDS}/{trend.id}", json={"status": "expired"})
    missing = sam.patch(f"{TRENDS}/{uuid.uuid4()}", json={"status": "approved"})

    assert approved.json()["status"] == "approved" and approved.json()["decided_at"]
    assert undone.json()["decided_at"] is None
    assert rejected.json()["status"] == "rejected"
    # Expiry is the scout's to decide, after 8 weeks unseen.
    assert expired.status_code == 422
    assert missing.status_code == 404


def test_the_run_log_shows_each_run_newest_first_with_the_months_credits(
    app: FastAPI, db: Session, sam: TestClient
) -> None:
    as_owner(app, "sam@example.com")
    first = agent_runs.start(db, "trend_scout", "schedule", NOW - timedelta(days=3))
    agent_runs.finish(first, "done", NOW - timedelta(days=3))
    first.search_credits = 8
    second = agent_runs.start(db, "trend_scout", "manual", NOW - timedelta(hours=1))
    second.steps = {"plan_queries": {"planned_by": "model", "queries": ["linen India"]}}
    agent_runs.finish(second, "stopped", NOW, "search_credits")
    second.search_credits = 3
    db.flush()

    found = sam.get(RUNS).json()

    assert [(r["trigger"], r["status"], r["stopped_by"]) for r in found["runs"]] == [
        ("manual", "stopped", "search_credits"),
        ("schedule", "done", None),
    ]
    assert found["runs"][0]["steps"]["plan_queries"]["queries"] == ["linen India"]
    month = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    assert found["credits_this_month"] == sum(
        r.search_credits for r in (first, second) if r.started_at >= month
    )
    assert found["credit_cap"] == get_settings().search_monthly_credit_cap
    assert sam.get(RUNS, params={"kind": "weekly_digest"}).json()["runs"] == []


def use_mail_settings(monkeypatch: pytest.MonkeyPatch, **changes: Any) -> None:
    settings = get_settings().model_copy(update=changes)
    monkeypatch.setattr(mail, "get_settings", lambda: settings)
    monkeypatch.setattr(run_report, "get_settings", lambda: settings)


def a_letter(to: str = "owner@example.com") -> Email:
    return Email(to=to, subject="Hello", text="Hello.", html="<p>Hello.</p>", key="k-1")


def test_until_a_domain_is_verified_only_listed_addresses_get_email(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_mail_settings(monkeypatch, email_allowlist=" Owner@Example.com ,")
    sender = FakeEmail()

    listed = mail.send(db, sender, a_letter("owner@example.com"), "run_report", NOW)
    other = mail.send(db, sender, a_letter("someone@example.com"), "digest", NOW)

    assert (listed.status, other.status) == ("sent", "held_by_allowlist")
    assert [e.to for e in sender.sent] == ["owner@example.com"]
    assert listed.provider_message_id == "fake-1" and other.provider_message_id is None


def test_the_daily_cap_holds_email_back(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    use_mail_settings(monkeypatch, email_allowlist="", email_daily_cap=1)
    sender = FakeEmail()

    first = mail.send(db, sender, a_letter(), "run_report", NOW)
    second = mail.send(db, sender, a_letter(), "run_report", NOW)

    assert (first.status, second.status) == ("sent", "held_by_daily_cap")
    assert len(sender.sent) == 1


def test_a_failed_send_is_recorded_without_the_address(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_mail_settings(monkeypatch, email_allowlist="")

    event = mail.send(db, FakeEmail(down=True), a_letter(), "run_report", NOW)

    assert (event.status, event.error, event.user_id) == ("failed", "down", None)
    assert "owner@example.com" not in json.dumps(
        {c.name: str(getattr(event, c.name)) for c in EmailEvent.__table__.columns}
    )


class Answer:
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body

    def read(self) -> bytes:
        return json.dumps(self.body).encode()

    def __enter__(self) -> Answer:
        return self

    def __exit__(self, *details: object) -> None:
        return None


def test_resend_gets_the_email_with_its_idempotency_key(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[urllib.request.Request] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> Answer:
        sent.append(request)
        return Answer({"id": "re-123"})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    letter = Email(
        to="owner@example.com",
        subject="Trend Scout: 1 new trend to review",
        text="Text.",
        html="<p>Text.</p>",
        headers={"List-Unsubscribe": "<https://example.com/u>"},
        key="run-report-1",
    )

    provider_id = ResendEmail("re-key", "WearWise <onboarding@resend.dev>").send(letter)

    [request] = sent
    assert provider_id == "re-123"
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_header("Authorization") == "Bearer re-key"
    assert request.get_header("Idempotency-key") == "run-report-1"
    assert isinstance(request.data, bytes)
    assert json.loads(request.data) == {
        "from": "WearWise <onboarding@resend.dev>",
        "to": ["owner@example.com"],
        "subject": "Trend Scout: 1 new trend to review",
        "text": "Text.",
        "html": "<p>Text.</p>",
        "headers": {"List-Unsubscribe": "<https://example.com/u>"},
    }


@pytest.mark.parametrize(("status", "reason", "tries"), [(403, "refused", 1), (503, "down", 2)])
def test_resend_failures_are_named_and_retried_once_when_busy(
    monkeypatch: pytest.MonkeyPatch, status: int, reason: str, tries: int
) -> None:
    calls: list[int] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> Answer:
        calls.append(status)
        raise urllib.error.HTTPError(request.full_url, status, "no", email.message.Message(), None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(EmailUnavailable) as raised:
        ResendEmail("re-key", "WearWise <onboarding@resend.dev>").send(a_letter())

    assert (raised.value.reason, len(calls)) == (reason, tries)


def scout_run(db: Session, saver: PostgresSaver, **settings: Any) -> AgentRun:
    from trend_support import found, plan

    run = agent_runs.start(db, "trend_scout", "schedule", NOW)
    db.flush()
    outcome = trend_scout.run(
        db,
        run,
        search(NOW.date()),
        ScriptedChatModel(script=[plan(), found()]),
        saver,
        NOW,
        sites=SITES,
        settings=get_settings().model_copy(update=settings),
    )
    if outcome.stopped_by:
        agent_runs.finish(run, "stopped", NOW + timedelta(seconds=42), outcome.stopped_by)
    else:
        agent_runs.finish(run, "done", NOW + timedelta(seconds=42))
    db.flush()
    return run


def test_the_run_report_says_what_was_searched_found_dropped_and_spent(
    db: Session, durable_checkpointer: PostgresSaver, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_mail_settings(monkeypatch, app_url="https://wearwise.example", trends_require_approval=True)
    run = scout_run(db, durable_checkpointer)

    report = run_report.scout_report(db, run, NOW)

    assert report.subject == "Trend Scout: 1 new trend to review"
    assert "on its schedule, for 42 seconds" in report.text
    assert "- men's linen co-ord trends India mild 2026" in report.text
    assert (
        "It read 3 pages from 2 searches. Not read: the same page again (3), blocked site (1), "
        "no date (1), older than 45 days (1)." in report.text
    )
    assert "- New, waiting for your approval: Linen co-ord sets" in report.text
    assert "Gold bags (fewer than two sites (1 quote not found in its page))" in report.text
    assert "2 search credits" in report.text
    assert "1 trend waiting for your approval: https://wearwise.example/admin/trends" in report.text
    # The same in HTML, escaped.
    assert "<li>men&#x27;s linen co-ord trends India mild 2026</li>" in report.html


def test_a_stopped_or_failed_run_says_why_in_the_subject(
    db: Session, durable_checkpointer: PostgresSaver, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_mail_settings(monkeypatch)
    stopped = scout_run(db, durable_checkpointer, search_monthly_credit_cap=1)
    failed = agent_runs.start(db, "weekly_digest", "manual", NOW)
    agent_runs.note_error(failed, "RuntimeError: the database went away")
    agent_runs.finish(failed, "failed", NOW)

    assert run_report.scout_report(db, stopped, NOW).subject == (
        "Trend Scout stopped early: the month's search credits ran out"
    )
    broken = run_report.scout_report(db, failed, NOW)
    assert broken.subject == "Trend Scout failed"
    assert "It failed: RuntimeError: the database went away" in broken.text


def test_the_report_goes_to_each_owner_and_is_recorded(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_mail_settings(monkeypatch, admin_emails="b@example.com, a@example.com", email_allowlist="")
    run = agent_runs.start(db, "trend_scout", "manual", NOW)
    agent_runs.finish(run, "done", NOW)
    sender = FakeEmail()

    sent = run_report.send_scout_report(db, run, sender, NOW)

    assert sent == 2
    assert [e.to for e in sender.sent] == ["a@example.com", "b@example.com"]
    assert sender.sent[0].key == f"run-report-{run.id}-a@example.com"
    events = db.scalars(select(EmailEvent).where(EmailEvent.kind == "run_report")).all()
    assert [(e.status, e.user_id) for e in events] == [("sent", None), ("sent", None)]


def test_with_no_owner_the_report_isnt_sent(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    use_mail_settings(monkeypatch, admin_emails="")
    run = agent_runs.start(db, "trend_scout", "manual", NOW)
    sender = FakeEmail()

    assert run_report.send_scout_report(db, run, sender, NOW) == 0
    assert sender.sent == []


def test_a_failed_run_is_still_reported_and_a_failed_report_changes_nothing(db: Session) -> None:
    reported: list[str] = []

    def failing(session: Session, run: AgentRun) -> Ended:
        raise RuntimeError("search broke")

    def report(session: Session, run: AgentRun) -> None:
        reported.append(run.status)

    def broken_report(session: Session, run: AgentRun) -> None:
        raise RuntimeError("email broke")

    code = runner.run_job(
        "trend_scout", failing, sessions=lambda: nullcontext(db), prepare=False, report=report
    )
    other = runner.run_job(
        "weekly_digest",
        lambda s, r: Ended(),
        sessions=lambda: nullcontext(db),
        prepare=False,
        report=broken_report,
    )

    assert (code, reported) == (1, ["failed"])
    assert other == 0
    assert agent_runs.latest(db, "weekly_digest")[0].status == "done"


def test_the_jobs_run_in_production_without_photo_storage_and_the_api_doesnt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("STORAGE_BACKEND", "none")
    settings = load_settings(env_file=None)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr(storage, "get_settings", lambda: settings)
    storage.get_storage.cache_clear()

    from app.main import create_app

    with pytest.raises(ConfigError, match="STORAGE_BACKEND must be s3 in production"):
        create_app()
    with pytest.raises(ConfigError, match="doesn't store photos"):
        storage.get_storage()
    storage.get_storage.cache_clear()


@pytest.mark.parametrize(
    ("variables", "message"),
    [
        ({"EMAIL_PROVIDER": "resend"}, "EMAIL_API_KEY, EMAIL_FROM"),
        (
            {"EMAIL_PROVIDER": "fake", "APP_ENV": "production", "STORAGE_BACKEND": "none"},
            "EMAIL_PROVIDER=fake isn't allowed in production",
        ),
        ({"SEARCH_PROVIDER": "tavily"}, "SEARCH_API_KEY"),
    ],
)
def test_email_and_search_settings_are_checked(
    monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], message: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    for name, value in variables.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ConfigError, match=message):
        load_settings(env_file=None)


def test_email_records_go_after_90_days(db: Session, sam: TestClient) -> None:
    add_item(sam, "chinos", "navy")
    old = EmailEvent(kind="run_report", status="sent")
    new = EmailEvent(kind="run_report", status="sent")
    db.add_all([old, new])
    db.flush()
    old.created_at = NOW - timedelta(days=91)
    db.flush()

    counts, _ = tidy(db, NOW)

    assert counts["email records"] == 1
    assert db.get(EmailEvent, new.id) is not None and db.get(EmailEvent, old.id) is None
