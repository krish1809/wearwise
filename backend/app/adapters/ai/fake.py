"""Scripted replies, for tests: each chat call takes the next turn from `turns` (a turn, a
function of the messages so far, or an exception to raise). With nothing scripted, it runs
one honest round trip, for trying the chat locally: it searches the wardrobe, then replies
with three of the items found, saying it's a test reply. Settings refuse it in production."""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.adapters.ai import ChatTurn, Message, Tagged, ToolCall, ToolSpec, Usage

Turn = ChatTurn | Callable[[Sequence[Message]], ChatTurn] | Exception


def say(text: str) -> ChatTurn:
    return ChatTurn(text, (), Usage(100, 20))


def call(tool: str, call_id: str = "call-1", /, **arguments: Any) -> ChatTurn:
    """A turn calling one tool; any keyword is an argument to the tool."""
    return ChatTurn("", (ToolCall(call_id, tool, arguments),), Usage(100, 20))


@dataclass
class FakeAI:
    turns: list[Turn] = field(default_factory=list)
    tags: dict[str, Any] | Exception | None = None
    # What each chat call was given: (system, messages, tool names, required tool).
    calls: list[tuple[str, list[Message], list[str], str | None]] = field(default_factory=list)
    images: list[bytes] = field(default_factory=list)

    def chat(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        require: str | None = None,
    ) -> ChatTurn:
        self.calls.append((system, list(messages), [t.name for t in tools], require))
        if not self.turns:
            return _round_trip(messages)
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        if callable(turn):
            return turn(messages)
        return turn

    def tag_image(
        self, image: bytes, media_type: str, schema: dict[str, Any], instructions: str
    ) -> Tagged:
        self.images.append(image)
        if isinstance(self.tags, Exception):
            raise self.tags
        return Tagged(dict(self.tags or {}), Usage(800, 60))


def _round_trip(messages: Sequence[Message]) -> ChatTurn:
    results = [result for message in messages for result in message.tool_results]
    if not results:
        return call("search_wardrobe", "fake-search", limit=3)
    try:
        found = json.loads(results[-1].content)["data"].get("items", [])
    except ValueError, KeyError, AttributeError:
        found = []
    cards = [{"type": "item", "item_id": item["id"]} for item in found[:3]]
    text = (
        "A test reply from the fake provider: here are three of your items."
        if cards
        else "A test reply from the fake provider: your wardrobe is empty so far."
    )
    return ChatTurn(
        "", (ToolCall("fake-reply", "reply", {"text": text, "cards": cards}),), Usage(100, 20)
    )
