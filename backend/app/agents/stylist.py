"""The stylist chat's turn as a LangGraph graph (docs/AGENTS.md, section 3; docs/AI.md, section 3).

    model -> tools -> model ... -> ground -> save -> confirm (waits)
                                    |  ^
                                    +--+  once, told what was wrong

The model is the M10 provider (app/adapters/ai: Anthropic over HTTPS, a scripted fake in tests),
called from the `model` step; the tools, the grounding check, and the proposals are the M10 ones
(app/services/stylist.py). What the graph adds:

- Every step is explicit, and the grounding check's one retry is an edge back to the model.
- A turn that proposes a change pauses at `confirm` (a LangGraph interrupt), checkpointed in
  Postgres, until the person says yes or no in the app, perhaps days later. Confirm and Not now
  resume it, and it ends once nothing it proposed is still waiting. A new message first answers
  whatever still waits with "not now".
- The proposals themselves are chat_actions rows, which decide what can still be confirmed;
  the paused run follows them, so a lost or pruned checkpoint never strands a proposal.
- The conversation itself stays in chat_messages, which the page, the export, and deletion
  read. The checkpoint holds only a waiting turn's few ids, and goes when the turn ends.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.adapters.ai import AIProvider, ChatTurn, Message, ToolCall, ToolResult
from app.adapters.weather import WeatherProvider
from app.models import ChatAction, ChatMessage, ChatThread, User
from app.services import ai_usage, checkpoints
from app.services import stylist as service


class TurnState(TypedDict, total=False):
    calls: int
    rejected: int
    # This turn's proposals still waiting for a yes or a no, by id.
    waiting: list[str]


@dataclass
class Talk:
    """One message's turn: what its steps share. The M10 turn (the database, the person, what
    the tools have shown), the provider, and the conversation, kept here rather than in the
    checkpoint, since chat_messages already holds it."""

    turn: service.Turn
    ai: AIProvider
    system: str
    messages: list[Message]
    text: str
    last: ChatTurn | None = None
    answer: tuple[str, list[dict[str, Any]]] | None = None
    asked: ChatMessage | None = None
    replied: ChatMessage | None = None

    def model(self, state: TurnState) -> TurnState:
        ai_usage.check_spend(self.turn.db, self.ai)
        forced = "reply" if state.get("calls", 0) >= service.MAX_TOOL_CALLS else None
        offered = [service.REPLY] if forced else [*service.TOOLS, service.REPLY]
        result = self.ai.chat(self.system, self.messages, offered, forced)
        self.turn.tokens_in += result.usage.input_tokens
        self.turn.tokens_out += result.usage.output_tokens
        ai_usage.record(self.turn.db, self.turn.user, result.usage)
        self.last = result
        return {}

    def after_model(self, state: TurnState) -> str:
        assert self.last is not None
        if not self.last.tool_calls or any(c.name == "reply" for c in self.last.tool_calls):
            return "ground"
        return "tools"

    def tools(self, state: TurnState) -> TurnState:
        assert self.last is not None
        results = [service.run_tool(self.turn, call) for call in self.last.tool_calls]
        self.messages += [
            Message("assistant", self.last.text, self.last.tool_calls),
            Message("user", tool_results=tuple(results)),
        ]
        return {"calls": state.get("calls", 0) + len(self.last.tool_calls)}

    def ground(self, state: TurnState) -> TurnState:
        """The grounding check: every id in the reply's cards came from a tool in this
        conversation and is the person's; the text holds no ids. Once wrong, the model is told
        why and tries again; twice, an apology and the tools' own cards go out instead."""
        assert self.last is not None
        reply = next((c for c in self.last.tool_calls if c.name == "reply"), None)
        if reply is None:
            # A plain answer without cards still has to keep ids out of its text.
            if not service.ground_text(self.turn, self.last.text):
                self.answer = (self.last.text.strip(), [])
                return {}
            reply = ToolCall("plain", "reply", {"text": self.last.text, "cards": []})
        text, cards, problems = service.check_reply(self.turn, reply.arguments)
        if not problems:
            self.answer = (text, cards)
            return {}
        rejected = state.get("rejected", 0) + 1
        if rejected > 1:
            self.answer = (service.APOLOGY, self.turn.fallback[: service.MAX_CARDS])
            return {"rejected": rejected}
        correction = ToolResult(
            reply.id,
            "Not shown: " + " ".join(problems) + " Use only ids that tools returned in this "
            "conversation, in cards, and call reply again.",
            is_error=True,
        )
        self.messages += [
            Message("assistant", self.last.text, (reply,)),
            Message("user", tool_results=(correction,)),
        ]
        return {"rejected": rejected}

    def after_ground(self, state: TurnState) -> str:
        return "save" if self.answer is not None else "model"

    def save(self, state: TurnState) -> TurnState:
        assert self.answer is not None
        text, cards = self.answer
        turn = self.turn
        self.asked = ChatMessage(thread_id=turn.thread.id, role="user", content=self.text)
        self.replied = ChatMessage(
            thread_id=turn.thread.id,
            role="assistant",
            content=text,
            cards=cards + [{"type": "action", "action_id": str(a.id)} for a in turn.actions],
            tool_calls=turn.calls,
            seen=sorted(turn.seen),
            tokens_in=turn.tokens_in,
            tokens_out=turn.tokens_out,
        )
        turn.db.add_all([self.asked, self.replied])
        turn.db.flush()
        # Recent conversations first.
        turn.thread.updated_at = func.now()
        return {"waiting": [str(action.id) for action in turn.actions]}


def confirm(state: TurnState) -> TurnState:
    """Wait for the person's yes or no to this turn's proposals. Resumed with the action just
    decided, or with everything settled as "not now". Nothing before the interrupt, since a
    resumed step runs again from its start."""
    decision: dict[str, Any] = interrupt({"waiting": state.get("waiting", [])})
    if decision.get("all"):
        return {"waiting": []}
    return {"waiting": [w for w in state.get("waiting", []) if w != decision.get("action_id")]}


def _waits(state: TurnState) -> str:
    return "confirm" if state.get("waiting") else END


def graph(
    talk: Talk | None, saver: BaseCheckpointSaver[Any]
) -> CompiledStateGraph[TurnState, None, TurnState, TurnState]:
    """The turn's graph. Resuming a turn that waits runs only `confirm`, so without a Talk the
    other steps are stand-ins that never run: the graph keeps the shape it paused in."""

    def stand_in(state: TurnState) -> Any:
        raise RuntimeError("Only the request that started a turn runs its steps.")

    builder = StateGraph(TurnState)
    builder.add_node("model", talk.model if talk else stand_in)
    builder.add_node("tools", talk.tools if talk else stand_in)
    builder.add_node("ground", talk.ground if talk else stand_in)
    builder.add_node("save", talk.save if talk else stand_in)
    builder.add_node("confirm", confirm)
    builder.add_edge(START, "model")
    builder.add_conditional_edges(
        "model", talk.after_model if talk else stand_in, ["ground", "tools"]
    )
    builder.add_edge("tools", "model")
    builder.add_conditional_edges(
        "ground", talk.after_ground if talk else stand_in, ["save", "model"]
    )
    builder.add_conditional_edges("save", _waits, ["confirm", END])
    builder.add_conditional_edges("confirm", _waits, ["confirm", END])
    return builder.compile(checkpointer=saver)


def _config(thread_id: uuid.UUID) -> Any:
    return {"configurable": {"thread_id": checkpoints.chat_thread(thread_id)}}


def send(
    db: Session,
    user: User,
    ai: AIProvider | None,
    weather: WeatherProvider,
    thread: ChatThread,
    text: str,
    today: date,
    saver: BaseCheckpointSaver[Any],
) -> tuple[ChatMessage, ChatMessage]:
    """Answer a message. Raises ai_usage.AIOff or AIUnavailable, leaving this turn's messages
    and proposals unsaved (the tokens already spent still count). Once the message is allowed,
    earlier proposals still waiting become "not now" either way."""
    ai_usage.check_message(db, user, ai)
    assert ai is not None
    settle(db, user, thread, saver)
    turn = service.Turn(db, user, weather, today, thread, seen=service.thread_seen(db, thread))
    talk = Talk(
        turn=turn,
        ai=ai,
        system=service.SYSTEM.format(today=today.isoformat()),
        messages=[*service.history(db, turn), Message("user", text)],
        text=text,
    )
    ai_usage.record(db, user, service.no_usage(), messages=1)
    compiled = graph(talk, saver)
    config = _config(thread.id)
    try:
        compiled.invoke({"calls": 0, "rejected": 0, "waiting": []}, config, durability="exit")
    except Exception:
        for action in turn.actions:
            db.delete(action)
        db.flush()
        saver.delete_thread(checkpoints.chat_thread(thread.id))
        raise
    if not compiled.get_state(config).next:
        saver.delete_thread(checkpoints.chat_thread(thread.id))
    assert talk.asked is not None and talk.replied is not None
    return talk.asked, talk.replied


def settle(db: Session, user: User, thread: ChatThread, saver: BaseCheckpointSaver[Any]) -> None:
    """Before a new message: proposals still waiting become "not now", and the turn waiting
    for them hears so and ends. The caller commits."""
    service.lapse(db, user, thread)
    compiled = graph(None, saver)
    config = _config(thread.id)
    if compiled.get_state(config).next:
        compiled.invoke(Command(resume={"all": True}), config, durability="exit")
        saver.delete_thread(checkpoints.chat_thread(thread.id))


def decided(action: ChatAction, saver: BaseCheckpointSaver[Any]) -> None:
    """After Confirm or Not now: the turn that proposed it hears the answer, and ends once
    nothing it proposed is still waiting. Nothing to do when no turn waits for this one (a
    newer message settled it, or its checkpoint was pruned)."""
    compiled = graph(None, saver)
    config = _config(action.thread_id)
    snapshot = compiled.get_state(config)
    if not snapshot.next or str(action.id) not in snapshot.values.get("waiting", []):
        return
    compiled.invoke(Command(resume={"action_id": str(action.id)}), config, durability="exit")
    if not compiled.get_state(config).next:
        saver.delete_thread(checkpoints.chat_thread(action.thread_id))
