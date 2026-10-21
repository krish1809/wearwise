"""The weekly email (docs/AGENTS.md, sections 5 and 6): the model's wording only once it passes
the check, the template when it doesn't or the model is off, at most one email a week, the
right people on the right day, batches, and a run that resumes where it died."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_digests import a_trend, dresses_for_college

from app.adapters.email import FakeEmail
from app.agents import checkpoint
from app.agents import digest as weekly
from app.agents.fake import ScriptedChatModel, tool_call
from app.core.config import get_settings
from app.jobs import runner
from app.jobs import weekly_digest as job
from app.models import AgentRun, Digest, User
from app.services import agent_runs, auth, digest_email, digests, mail
from app.services import profile as profiles

# A Sunday morning in India.
NOW = datetime(2026, 10, 25, 2, 37, tzinfo=UTC)
TODAY = NOW.date()
FINE = "Olive cotton chinos would go with much of what you already own."


def wording(sentence: str = FINE, subject: str = "Worth a look: olive chinos") -> AIMessage:
    return tool_call(
        "Wording",
        {
            "subject": subject,
            "intro": "What's in fashion now, against what you own.",
            "sentences": [sentence],
        },
    )


@pytest.fixture
def open_mail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Email to anyone, as once a domain is verified, whatever the local settings say."""
    settings = get_settings().model_copy(
        update={"email_allowlist": "", "email_daily_cap": 90, "app_url": "https://wearwise.example"}
    )
    for module in (mail, digest_email):
        monkeypatch.setattr(module, "get_settings", lambda: settings)


@pytest.fixture
def the_job(
    monkeypatch: pytest.MonkeyPatch, durable_checkpointer: PostgresSaver, outbox: FakeEmail
) -> ScriptedChatModel:
    """The job with a scripted model, the test's outbox, and a checkpointer of its own."""
    model = ScriptedChatModel()

    @contextmanager
    def saver(url: str | None = None) -> Iterator[PostgresSaver]:
        yield durable_checkpointer

    monkeypatch.setattr(checkpoint, "saver", saver)
    monkeypatch.setattr(job, "get_chat_model", lambda: model)
    monkeypatch.setattr(job, "get_email_sender", lambda: outbox)
    monkeypatch.setattr(job, "now", lambda: NOW)
    return model


def subscribe(db: Session, email: str, weekday: int = TODAY.weekday()) -> User:
    person = db.scalars(select(User).where(User.email == email)).one()
    person.email_verified_at = NOW
    profile = profiles.get_or_create_profile(db, person)
    profile.digest_opted_in_at = NOW
    profile.digest_weekday = weekday
    db.flush()
    return person


def a_run(db: Session) -> AgentRun:
    """A new run of the job, the last one finished first, as the runner would have."""
    for earlier in agent_runs.latest(db, "weekly_digest"):
        if earlier.status == "running":
            agent_runs.finish(earlier, "done", NOW)
    db.flush()
    run = agent_runs.start(db, "weekly_digest", "schedule", NOW)
    db.flush()
    return run


def latest(db: Session, person: User) -> Digest:
    found = digests.latest(db, person)
    assert found is not None
    return found


@pytest.mark.usefixtures("open_mail")
def test_the_email_goes_out_in_the_models_words_once_they_pass_the_check(
    db: Session, sam: TestClient, the_job: ScriptedChatModel, outbox: FakeEmail
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    person = subscribe(db, "sam@example.com")
    the_job.script = [wording()]

    job.work(db, a_run(db))

    [letter] = outbox.sent
    digest = latest(db, person)
    assert letter.subject == "Worth a look: olive chinos"
    assert FINE in letter.text
    assert (digest.status, digest.wording, digest.sent_at) == ("sent", "model", NOW)
    # The model was given the picks, never the person's address or name.
    said = " ".join(str(m.content) for sent in the_job.sent for m in sent)
    assert "sam@example.com" not in said and "Olive chinos" in said


@pytest.mark.usefixtures("open_mail")
def test_a_made_up_number_is_tried_again_then_replaced_by_the_template(
    db: Session, sam: TestClient, the_job: ScriptedChatModel, outbox: FakeEmail
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    person = subscribe(db, "sam@example.com")
    made_up = "Olive cotton chinos would make 977 new outfits."
    the_job.script = [wording(made_up), wording(made_up)]

    job.work(db, a_run(db))

    [letter] = outbox.sent
    digest = latest(db, person)
    assert len(the_job.sent) == 2
    assert "977" in str(the_job.sent[1][-1].content)
    assert digest.wording == "template"
    assert letter.subject == digest.subject == "Worth a look this week: olive cotton chinos"
    assert "977" not in letter.text


@pytest.mark.usefixtures("open_mail")
def test_a_second_try_that_passes_is_used(
    db: Session, sam: TestClient, the_job: ScriptedChatModel, outbox: FakeEmail
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    subscribe(db, "sam@example.com")
    the_job.script = [wording("Hurry: olive chinos are a must-have."), wording()]

    job.work(db, a_run(db))

    assert outbox.sent[0].subject == "Worth a look: olive chinos"


@pytest.mark.parametrize("model", ["down", "off"])
@pytest.mark.usefixtures("open_mail")
def test_with_the_model_down_or_off_the_template_goes_out(
    db: Session,
    sam: TestClient,
    the_job: ScriptedChatModel,
    outbox: FakeEmail,
    monkeypatch: pytest.MonkeyPatch,
    model: str,
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    person = subscribe(db, "sam@example.com")
    if model == "down":
        the_job.down = True
    else:
        monkeypatch.setattr(job, "get_chat_model", lambda: None)

    job.work(db, a_run(db))

    [letter] = outbox.sent
    assert latest(db, person).wording == "template"
    assert letter.subject == "Worth a look this week: olive cotton chinos"


@pytest.mark.usefixtures("open_mail")
def test_nothing_worth_it_means_no_email(
    db: Session, sam: TestClient, the_job: ScriptedChatModel, outbox: FakeEmail
) -> None:
    dresses_for_college(sam)
    subscribe(db, "sam@example.com")
    run = a_run(db)

    job.work(db, run)

    assert outbox.sent == [] and the_job.sent == []
    assert run.steps["send"]["nothing"] == 1


@pytest.mark.usefixtures("open_mail")
def test_a_second_run_in_the_same_week_sends_nothing(
    db: Session, sam: TestClient, the_job: ScriptedChatModel, outbox: FakeEmail
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    subscribe(db, "sam@example.com")
    the_job.script = [wording(), wording()]

    job.work(db, a_run(db))
    job.work(db, a_run(db))

    assert len(outbox.sent) == 1


def test_who_is_due_today(db: Session, sam: TestClient, ana: TestClient) -> None:
    # A Monday, so yesterday's late email is in the week before.
    monday = NOW + timedelta(days=1)
    day = monday.date()
    today = subscribe(db, "sam@example.com", day.weekday())
    late = subscribe(db, "ana@example.com", (day - timedelta(days=1)).weekday())
    for email, weekday, confirmed, opted in [
        ("three-days-ago@example.com", (day - timedelta(days=3)).weekday(), True, True),
        ("tomorrow@example.com", (day + timedelta(days=1)).weekday(), True, True),
        ("unconfirmed@example.com", day.weekday(), False, True),
        ("turned-off@example.com", day.weekday(), True, False),
    ]:
        other = auth.register(db, email=email, password="a long test password", name=None)
        other.email_verified_at = NOW if confirmed else None
        profile = profiles.get_or_create_profile(db, other)
        profile.digest_weekday = weekday
        profile.digest_opted_in_at = NOW if opted else None
    db.flush()

    found = {(d.user.id, d.week) for d in job.due(db, monday)}

    assert found == {
        (today.id, digests.week_of(day)),
        # A day late, it still belongs to the week of its day: Sunday's, not this Monday's.
        (late.id, digests.week_of(day - timedelta(days=1))),
    }
    assert digests.week_of(day) != digests.week_of(day - timedelta(days=1))


@pytest.mark.usefixtures("open_mail")
def test_the_batch_cap_leaves_the_rest_for_the_next_run(
    db: Session,
    sam: TestClient,
    ana: TestClient,
    the_job: ScriptedChatModel,
    outbox: FakeEmail,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for client, email in ((sam, "sam@example.com"), (ana, "ana@example.com")):
        dresses_for_college(client)
        subscribe(db, email)
    a_trend(db, "Olive chinos")
    capped = get_settings().model_copy(update={"digest_batch_cap": 1})
    monkeypatch.setattr(job, "get_settings", lambda: capped)
    run = a_run(db)

    ended = job.work(db, run)
    job.work(db, a_run(db))

    assert ended == runner.Ended("stopped", "batch_cap")
    assert run.steps["send"]["due"] == 2 and run.steps["send"]["over_cap"] == 1
    assert len(outbox.sent) == 2


@pytest.mark.usefixtures("open_mail")
def test_one_persons_failure_doesnt_stop_the_others_or_name_them(
    db: Session,
    sam: TestClient,
    ana: TestClient,
    the_job: ScriptedChatModel,
    outbox: FakeEmail,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for client, email in ((sam, "sam@example.com"), (ana, "ana@example.com")):
        dresses_for_college(client)
        subscribe(db, email)
    a_trend(db, "Olive chinos")
    build = digests.build

    def broken(session: Session, person: User, *args: Any) -> Digest:
        if person.email == "sam@example.com":
            raise RuntimeError("sam@example.com broke")
        return build(session, person, *args)

    monkeypatch.setattr(digests, "build", broken)
    run = a_run(db)
    # Committed, as everything is by the time a job runs: the job undoes only a failed email.
    db.commit()

    job.work(db, run)

    assert [letter.to for letter in outbox.sent] == ["ana@example.com"]
    assert run.errors == ["one email: RuntimeError"]
    assert run.steps["send"]["failed"] == 1


@pytest.mark.usefixtures("open_mail")
def test_a_run_that_died_after_the_check_resumes_at_send_without_asking_again(
    db: Session,
    sam: TestClient,
    the_job: ScriptedChatModel,
    outbox: FakeEmail,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    person = subscribe(db, "sam@example.com")
    the_job.script = [wording()]
    render = digest_email.render
    calls: list[int] = []

    def dies_once(*args: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("the process died")
        return render(*args)

    monkeypatch.setattr(digest_email, "render", dies_once)

    job.work(db, a_run(db))
    asked = len(the_job.sent)
    job.work(db, a_run(db))

    [letter] = outbox.sent
    assert asked == 1 and len(the_job.sent) == 1
    assert letter.subject == "Worth a look: olive chinos"
    assert latest(db, person).status == "sent"


def test_an_email_the_allowlist_holds_is_tried_again_by_the_next_run(
    db: Session,
    sam: TestClient,
    the_job: ScriptedChatModel,
    outbox: FakeEmail,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    person = subscribe(db, "sam@example.com")
    held = get_settings().model_copy(update={"email_allowlist": "owner@example.com"})
    for module in (mail, digest_email):
        monkeypatch.setattr(module, "get_settings", lambda: held)

    job.work(db, a_run(db))
    still_due = [d.user.id for d in job.due(db, NOW)]

    assert outbox.sent == [] and latest(db, person).status == "held"
    assert still_due == [person.id]


@pytest.mark.usefixtures("open_mail")
def test_the_job_records_its_counts_through_the_runner(
    db: Session, sam: TestClient, the_job: ScriptedChatModel, outbox: FakeEmail
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    subscribe(db, "sam@example.com")
    the_job.script = [wording()]

    code = runner.run_job("weekly_digest", job.work, sessions=lambda: _same(db), prepare=False)

    [run] = agent_runs.latest(db, "weekly_digest")
    assert code == 0 and run.status == "done"
    assert run.steps["send"] == {"due": 1, "over_cap": 0, "sent": 1, "wording_model": 1}
    assert run.tokens_in == 100 and run.tokens_out == 20


@contextmanager
def _same(db: Session) -> Iterator[Session]:
    yield db


def test_the_wording_check() -> None:
    given = {
        "picks": [{"n": 1, "new_outfits": 4, "usual_spend_rupees": 1500, "reasons": []}],
        "template": {},
    }

    def problems(sentence: str, subject: str = "Your picks") -> list[str]:
        return weekly.check_wording(
            weekly.Wording(subject=subject, intro="This week.", sentences=[sentence]), given
        )

    assert problems("Four new outfits, about ₹1,500, n 1.") == []
    assert problems("It makes 4 outfits under 1,500.") == []
    assert problems("It makes 9 outfits.") == ["These numbers aren't in the data: 9."]
    assert problems("See https://shop.example now.") == ["No links or email addresses."]
    assert problems("A flattering cut.") == ["Nothing about bodies."]
    assert problems("Don't miss the sale!") == ["No pressure to buy."]
    assert problems("Fine.", subject="x" * 71) == ["The subject is over 70 characters."]
