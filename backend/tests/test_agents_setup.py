"""The agents' groundwork (docs/AGENTS.md, sections 2 and 6): checkpoints in Postgres that a
run can pause and resume from and that leave with their person, the scripted model, tracing that
stays off for wardrobe data, and the job runner's one-run-at-a-time rule."""

import uuid
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from conftest import BACKEND_DIR
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt
from langsmith.utils import tracing_is_enabled
from pydantic import BaseModel
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.adapters.ai import Usage
from app.adapters.storage import MemoryStorage
from app.agents import model as models
from app.agents import tracing
from app.agents.fake import REPLY, ModelDown, ScriptedChatModel, tool_call
from app.core.config import ConfigError, Settings, get_settings, load_settings
from app.jobs import runner
from app.jobs.runner import Ended
from app.models import AgentRun, Base, ChatThread, ErrorEvent, User
from app.services import account, agent_runs, checkpoints


class Asked(TypedDict, total=False):
    question: str
    answer: str


def ask(state: Asked) -> Asked:
    return {"answer": interrupt({"question": state["question"]})}


def asking_graph(saver: PostgresSaver) -> CompiledStateGraph[Any, Any, Any, Any]:
    """The smallest graph that pauses: one step that waits for an answer."""
    graph = StateGraph(Asked)
    graph.add_node("ask", ask)
    graph.add_edge(START, "ask")
    graph.add_edge("ask", END)
    return graph.compile(checkpointer=saver)


def pause(saver: PostgresSaver, thread_id: str) -> None:
    asking_graph(saver).invoke({"question": "Keep it?"}, {"configurable": {"thread_id": thread_id}})


def threads(db: Session) -> set[str]:
    return set(db.scalars(text("SELECT DISTINCT thread_id FROM checkpoints")))


def test_migrations_match_the_models_and_leave_the_checkpoint_tables_alone(
    engine: Engine, migrated_database: str
) -> None:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.attributes["database_url"] = migrated_database
    # Raises if autogenerate would change anything, through the project's own env.py.
    command.check(config)

    with engine.connect() as connection:
        unfiltered = MigrationContext.configure(connection)
        dropped = {
            op[1].name
            for op in compare_metadata(unfiltered, Base.metadata)
            if op[0] == "remove_table"
        }
    # Without the filter, autogenerate would drop the library's tables.
    assert dropped == set(checkpoints.TABLES)


def test_a_paused_run_is_kept_in_postgres_and_resumes_after_a_restart(
    checkpointer: PostgresSaver,
) -> None:
    config: Any = {"configurable": {"thread_id": "scout:resume"}}
    first = asking_graph(checkpointer).invoke({"question": "Keep it?"}, config)

    # A new graph, as after the process restarts, finds the pause and its question.
    restarted = asking_graph(checkpointer)
    [waiting] = restarted.get_state(config).interrupts
    resumed = restarted.invoke(Command(resume="yes"), config)

    assert "__interrupt__" in first
    assert waiting.value == {"question": "Keep it?"}
    assert resumed == {"question": "Keep it?", "answer": "yes"}


def test_the_apis_own_checkpointer_keeps_a_waiting_turn_until_it_ends() -> None:
    """The API's checkpointer on its connection pool, which the other tests swap out."""
    from app.agents import stylist
    from app.agents.checkpoint import close_shared, get_checkpointer, shared

    saver = get_checkpointer()
    graph = stylist.graph(None, saver)
    thread = checkpoints.chat_thread(uuid.uuid4())
    config: Any = {"configurable": {"thread_id": thread}}
    try:
        graph.update_state(config, {"waiting": ["a"]}, as_node="save")
        graph.invoke(None, config, durability="exit")
        paused = graph.get_state(config)
        graph.invoke(Command(resume={"action_id": "a"}), config, durability="exit")
        ended = graph.get_state(config)
        saver.delete_thread(thread)

        assert (paused.next, paused.values) == (("confirm",), {"waiting": ["a"]})
        assert (ended.next, ended.values) == ((), {"waiting": []})
        assert saver.get_tuple(config) is None
    finally:
        saver.delete_thread(thread)
        close_shared()
    assert shared.cache_info().currsize == 0 and saver.conn.closed


def test_deleting_an_account_deletes_its_checkpoints_and_no_one_elses(
    db: Session, checkpointer: PostgresSaver, sam: TestClient, ana: TestClient
) -> None:
    def chat(email: str) -> tuple[User, str]:
        user = db.scalars(select(User).where(User.email == email)).one()
        thread = ChatThread(user_id=user.id, title="Hello")
        db.add(thread)
        db.flush()
        return user, checkpoints.chat_thread(thread.id)

    sam_user, sam_chat = chat("sam@example.com")
    ana_user, ana_chat = chat("ana@example.com")
    sam_digest = checkpoints.digest_thread(sam_user.id, "2026-W44")
    ana_digest = checkpoints.digest_thread(ana_user.id, "2026-W44")
    for thread_id in (sam_chat, sam_digest, ana_chat, ana_digest):
        pause(checkpointer, thread_id)

    account.delete_account(db, MemoryStorage(), sam_user)

    assert threads(db) == {ana_chat, ana_digest}
    for table in checkpoints.THREAD_TABLES:
        left = db.scalar(
            text(f"SELECT count(*) FROM {table} WHERE thread_id = ANY(:ids)"),
            {"ids": [sam_chat, sam_digest]},
        )
        assert left == 0


def test_checkpoints_left_for_a_day_are_removed(db: Session, checkpointer: PostgresSaver) -> None:
    pause(checkpointer, "scout:left-behind")
    now = datetime.now(UTC)

    kept = checkpoints.remove_stale(db, now)
    removed = checkpoints.remove_stale(db, now + checkpoints.KEPT_FOR + timedelta(minutes=1))

    assert (kept, removed) == (0, 1)
    assert "scout:left-behind" not in threads(db)


def test_the_scripted_model_answers_in_order_and_remembers_what_it_was_sent() -> None:
    model = ScriptedChatModel(script=[AIMessage(content="Linen, for the heat.")])

    first = model.invoke("What should I wear?")
    second = model.invoke("And tomorrow?")

    assert (first.content, second.content) == ("Linen, for the heat.", REPLY)
    assert [m[0].content for m in model.sent] == ["What should I wear?", "And tomorrow?"]
    assert models.usage(first) == Usage(100, 20)


class Pick(BaseModel):
    name: str


def test_structured_output_comes_from_a_scripted_call() -> None:
    model = ScriptedChatModel(script=[tool_call("Pick", {"name": "olive chinos"})])

    found = model.with_structured_output(Pick, include_raw=True).invoke("Pick one")
    nothing = model.with_structured_output(Pick, include_raw=True).invoke("Again")

    assert isinstance(found, dict) and isinstance(nothing, dict)
    assert found["parsed"] == Pick(name="olive chinos")
    assert model.offered == [["Pick"], ["Pick"]]
    # With nothing scripted, the honest reply has no call to parse: callers fall back.
    assert nothing["parsed"] is None


def test_a_model_that_is_down_raises() -> None:
    with pytest.raises(ModelDown):
        ScriptedChatModel(down=True).invoke("Hello")


def use_settings(monkeypatch: pytest.MonkeyPatch, **changes: Any) -> Settings:
    settings = get_settings().model_copy(update=changes)
    for module in (models, tracing):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    models.get_chat_model.cache_clear()
    return settings


def test_the_model_follows_the_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    use_settings(monkeypatch, ai_provider="off")
    off = models.get_chat_model()
    use_settings(monkeypatch, ai_provider="fake")
    fake = models.get_chat_model()
    use_settings(
        monkeypatch, ai_provider="anthropic", ai_api_key="test-key", ai_model_chat="claude-test"
    )
    real = models.get_chat_model()
    models.get_chat_model.cache_clear()

    assert off is None
    assert isinstance(fake, ScriptedChatModel)
    assert real is not None and getattr(real, "model", None) == "claude-test"


def test_tracing_stays_off_even_when_the_host_turns_it_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    use_settings(monkeypatch, agent_tracing="off")

    with tracing.traced("trend_scout"):
        assert not tracing_is_enabled()


def test_production_traces_only_the_trend_scout(monkeypatch: pytest.MonkeyPatch) -> None:
    use_settings(
        monkeypatch, agent_tracing="langsmith", langsmith_api_key="test-key", app_env="production"
    )

    with tracing.traced("weekly_digest"):
        digest = tracing_is_enabled()
    with tracing.traced("trend_scout"):
        scout = tracing_is_enabled()

    assert (scout, digest) == (True, False)
    assert not tracing.allowed("stylist")


def test_tracing_needs_its_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("AGENT_TRACING", "langsmith")

    with pytest.raises(ConfigError, match="LANGSMITH_API_KEY"):
        load_settings(env_file=None)


def in_test(db: Session) -> runner.Sessions:
    return lambda: nullcontext(db)


def test_a_job_records_its_run(db: Session) -> None:
    def work(session: Session, run: AgentRun) -> Ended:
        run.steps = {"plan_queries": {"queries": 3}}
        return Ended()

    code = runner.run_job("trend_scout", work, sessions=in_test(db), prepare=False)

    [run] = agent_runs.latest(db, "trend_scout")
    assert code == 0
    assert (run.status, run.trigger, run.steps) == (
        "done",
        "manual",
        {"plan_queries": {"queries": 3}},
    )
    assert run.finished_at is not None


def test_a_scheduled_run_says_so_and_a_limit_is_recorded(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")

    runner.run_job(
        "trend_scout",
        lambda session, run: Ended("stopped", "search_credits"),
        sessions=in_test(db),
        prepare=False,
    )

    [run] = agent_runs.latest(db, "trend_scout")
    assert (run.trigger, run.status, run.stopped_by) == ("schedule", "stopped", "search_credits")


def test_a_second_run_of_the_same_kind_steps_aside(db: Session) -> None:
    agent_runs.start(db, "trend_scout", "schedule", runner.now())
    db.flush()
    called: list[str] = []

    def work(session: Session, run: AgentRun) -> Ended:
        called.append(run.kind)
        return Ended()

    code = runner.run_job("trend_scout", work, sessions=in_test(db), prepare=False)
    other = runner.run_job("weekly_digest", work, sessions=in_test(db), prepare=False)

    assert (code, other) == (0, 0)
    # Only the other kind ran; the first stepped aside without a second row.
    assert called == ["weekly_digest"]
    assert [r.status for r in agent_runs.latest(db, "trend_scout")] == ["running"]


def test_a_run_left_running_lapses_and_the_next_goes_ahead(db: Session) -> None:
    stuck = agent_runs.start(
        db, "trend_scout", "schedule", runner.now() - agent_runs.LAPSE - timedelta(minutes=5)
    )
    db.flush()

    code = runner.run_job("trend_scout", lambda s, r: Ended(), sessions=in_test(db), prepare=False)

    db.refresh(stuck)
    assert code == 0
    assert (stuck.status, stuck.stopped_by) == ("failed", "lapsed")
    assert agent_runs.latest(db, "trend_scout")[0].status == "done"


def test_a_failed_run_is_recorded_undone_and_fails_the_process(db: Session) -> None:
    marker = f"half-done {uuid.uuid4()}"

    def work(session: Session, run: AgentRun) -> Ended:
        session.add(ErrorEvent(source="server", kind="Test", message=marker))
        session.flush()
        raise RuntimeError("the search service is down")

    code = runner.run_job("trend_scout", work, sessions=in_test(db), prepare=False)

    [run] = agent_runs.latest(db, "trend_scout")
    assert code == 1
    assert (run.status, run.errors) == ("failed", ["RuntimeError: the search service is down"])
    # What the work did before failing is undone; only the record of the failure stays.
    assert db.scalar(select(ErrorEvent).where(ErrorEvent.message == marker)) is None
