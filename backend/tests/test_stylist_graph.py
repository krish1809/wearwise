"""The stylist's turn as a LangGraph graph (docs/AGENTS.md, section 3): a turn that proposes a
change waits, checkpointed, until the person decides; a new message answers whatever still
waits with "not now"; and the trend and weekly-picks tools. The M10 behaviour, which the graph
keeps, is in test_stylist.py."""

import json
import uuid
from datetime import date, timedelta
from typing import Any

from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_digests import a_trend, dresses_for_college
from test_stylist import SEND, last_result, outfit_items, reply

from app.adapters.ai import AIUnavailable, ChatTurn, ToolCall, Usage
from app.adapters.ai.fake import FakeAI, call
from app.agents import stylist as agent
from app.models import ChatAction, Outfit, PlanDay, TrendSource
from app.services import checkpoints, wear

ACTIONS = "/api/v1/chat/actions"


def waiting(saver: PostgresSaver, thread_id: str) -> list[str] | None:
    """The proposals a paused turn in this conversation waits for; None when no turn waits."""
    config: Any = {"configurable": {"thread_id": checkpoints.chat_thread(uuid.UUID(thread_id))}}
    snapshot = agent.graph(None, saver).get_state(config)
    return list(snapshot.values["waiting"]) if snapshot.next else None


def kept(db: Session, thread_id: str) -> int:
    """How many checkpoints this conversation has, as the app's own connection sees them."""
    found = db.scalar(
        text("SELECT count(*) FROM checkpoints WHERE thread_id = :id"),
        {"id": checkpoints.chat_thread(uuid.UUID(thread_id))},
    )
    return int(found)


def save_and_plan(found: dict[str, dict[str, Any]]) -> ChatTurn:
    """One model turn proposing two changes at once."""
    ids = [found[k]["id"] for k in ("shirt", "chinos", "loafers")]
    tomorrow = (wear.today() + timedelta(days=1)).isoformat()
    return ChatTurn(
        "",
        (
            ToolCall("call-1", "propose_save_outfit", {"item_ids": ids, "name": "Easy"}),
            ToolCall("call-2", "propose_plan_outfit", {"item_ids": ids, "date": tomorrow}),
        ),
        Usage(100, 20),
    )


def test_a_turn_that_proposes_waits_until_each_proposal_is_decided(
    sam: TestClient, ai: FakeAI, db: Session, durable_checkpointer: PostgresSaver
) -> None:
    found = outfit_items(sam)
    ai.turns = [save_and_plan(found), reply("Two things to confirm below.")]

    sent = sam.post(SEND, json={"text": "Save it and wear it tomorrow"}).json()

    thread_id = sent["thread"]["id"]
    save, plan = (card["action"] for card in sent["messages"][1]["cards"])
    assert waiting(durable_checkpointer, thread_id) == [save["id"], plan["id"]]

    assert sam.post(f"{ACTIONS}/{save['id']}/confirm").json()["status"] == "done"
    assert waiting(durable_checkpointer, thread_id) == [plan["id"]]
    assert sam.post(f"{ACTIONS}/{plan['id']}/cancel").json()["status"] == "cancelled"
    # Nothing waits any more, so the turn ended and its checkpoints went with it.
    assert waiting(durable_checkpointer, thread_id) is None
    assert kept(db, thread_id) == 0
    assert db.scalar(select(func.count()).select_from(Outfit)) == 1
    assert db.scalar(select(func.count()).select_from(PlanDay)) == 0


def test_a_turn_without_proposals_keeps_no_checkpoint(
    sam: TestClient, ai: FakeAI, db: Session
) -> None:
    outfit_items(sam)
    ai.turns = [call("search_wardrobe"), reply("You have three pieces.")]

    sent = sam.post(SEND, json={"text": "What do I own?"}).json()

    assert kept(db, sent["thread"]["id"]) == 0


def test_a_new_message_answers_what_still_waits_with_not_now(
    sam: TestClient, ai: FakeAI, db: Session, durable_checkpointer: PostgresSaver
) -> None:
    found = outfit_items(sam)
    ai.turns = [save_and_plan(found), reply("Confirm below.")]
    first = sam.post(SEND, json={"text": "Save it and wear it tomorrow"}).json()
    thread_id = first["thread"]["id"]
    save, plan = (card["action"] for card in first["messages"][1]["cards"])
    sam.post(f"{ACTIONS}/{save['id']}/confirm")
    ai.turns = [reply("Something warmer, then.")]

    sam.post(SEND, json={"thread_id": thread_id, "text": "Actually, something warmer?"})

    # The plan can't be confirmed now that the conversation has moved on; the saved outfit
    # stays saved.
    assert sam.post(f"{ACTIONS}/{plan['id']}/confirm").status_code == 409
    statuses = dict(db.execute(select(ChatAction.kind, ChatAction.status)).all())
    assert statuses == {"save_outfit": "done", "plan_outfit": "cancelled"}
    assert waiting(durable_checkpointer, thread_id) is None
    # The model was told how each proposal ended.
    told = ai.calls[-1][1][-2].text
    assert "done)" in told and "cancelled)" in told


def test_a_proposal_whose_checkpoint_is_gone_still_follows_the_rules(
    sam: TestClient, ai: FakeAI, db: Session, durable_checkpointer: PostgresSaver
) -> None:
    found = outfit_items(sam)
    ai.turns = [save_and_plan(found), reply("Confirm below.")]
    first = sam.post(SEND, json={"text": "Save it and wear it tomorrow"}).json()
    thread_id = first["thread"]["id"]
    save, plan = (card["action"] for card in first["messages"][1]["cards"])
    # Housekeeping prunes a turn nobody came back to after a day.
    durable_checkpointer.delete_thread(checkpoints.chat_thread(uuid.UUID(thread_id)))

    confirmed = sam.post(f"{ACTIONS}/{save['id']}/confirm")
    ai.turns = [reply("Noted.")]
    sam.post(SEND, json={"thread_id": thread_id, "text": "Thanks"})

    assert confirmed.json()["status"] == "done"
    assert sam.post(f"{ACTIONS}/{plan['id']}/confirm").status_code == 409


def test_a_failed_message_leaves_no_checkpoint_but_still_moves_on(
    sam: TestClient, ai: FakeAI, db: Session
) -> None:
    found = outfit_items(sam)
    ai.turns = [save_and_plan(found), reply("Confirm below.")]
    first = sam.post(SEND, json={"text": "Save it and wear it tomorrow"}).json()
    thread_id = first["thread"]["id"]
    ids = [found[k]["id"] for k in ("shirt", "chinos", "loafers")]
    ai.turns = [call("propose_save_outfit", item_ids=ids), AIUnavailable("down")]

    failed = sam.post(SEND, json={"thread_id": thread_id, "text": "Save it again"})

    assert failed.status_code == 503
    # The failed turn's own proposal wasn't kept, and neither was a checkpoint for it; the
    # earlier proposals were answered with "not now" when the message was sent.
    assert kept(db, thread_id) == 0
    statuses = list(db.scalars(select(ChatAction.status)))
    assert statuses == ["cancelled", "cancelled"]


def test_deleting_a_conversation_deletes_the_turn_waiting_in_it(
    sam: TestClient, ai: FakeAI, db: Session
) -> None:
    found = outfit_items(sam)
    ai.turns = [save_and_plan(found), reply("Confirm below.")]
    thread_id = sam.post(SEND, json={"text": "Save it"}).json()["thread"]["id"]
    assert kept(db, thread_id) > 0

    assert sam.delete(f"/api/v1/chat/threads/{thread_id}").status_code == 204

    assert kept(db, thread_id) == 0


def test_get_trends_gives_approved_trends_with_where_they_were_seen(
    sam: TestClient, ai: FakeAI, db: Session
) -> None:
    dresses_for_college(sam)
    olive = a_trend(db, "Olive chinos")
    a_trend(db, "Waiting trend", status="pending")
    a_trend(db, "Womenswear only", sections=["womenswear"])
    db.add(
        TrendSource(
            trend_id=olive.id,
            url="https://www.example.com/olive",
            domain="example.com",
            title="Olive is everywhere",
            published_on=date(2026, 10, 1),
            quote="olive chinos",
        )
    )
    db.flush()
    ai.turns = [call("get_trends", category_id="chinos"), reply("Olive chinos, seen on one site.")]

    sam.post(SEND, json={"text": "What's in fashion?"})

    given = json.loads(ai.calls[1][1][-1].tool_results[0].content)["data"]
    assert [t["name"] for t in given["trends"]] == ["Olive chinos"]
    [trend] = given["trends"]
    assert trend["seen_on"] == [
        {"site": "example.com", "title": "Olive is everywhere", "published": "2026-10-01"}
    ]
    assert trend["pieces"] == ["Chinos"] and trend["colours"] == ["Olive"]


def test_get_latest_digest_gives_the_persons_own_picks_and_pieces(
    sam: TestClient, ana: TestClient, ai: FakeAI, db: Session
) -> None:
    owned = dresses_for_college(sam)
    a_trend(db, "Beige chinos are back", color_families=["beige"])
    sam.post("/api/v1/digests/preview")
    chinos = owned["beige chinos"]["id"]
    ai.turns = [
        call("get_latest_digest"),
        lambda messages: reply(
            "Your beige chinos are in fashion again.",
            {"type": "item", "item_id": last_result(messages)["picks"][0]["their_item_ids"][0]},
        ),
    ]

    answer = sam.post(SEND, json={"text": "What were my picks?"}).json()["messages"][1]

    given = json.loads(ai.calls[1][1][-1].tool_results[0].content)["data"]
    assert [(p["piece"], p["kind"]) for p in given["picks"]] == [("Beige chinos", "already theirs")]
    # The person's own piece from the picks can be shown as a card.
    assert answer["cards"][0]["items"][0]["id"] == chinos
    # Someone without picks hears so; nobody sees anyone else's.
    ai.turns = [call("get_latest_digest"), reply("No picks yet.")]
    ana.post(SEND, json={"text": "What were my picks?"})
    theirs = json.loads(ai.calls[-1][1][-1].tool_results[0].content)["data"]
    assert theirs["picks"] == [] and "No weekly picks yet" in theirs["note"]
