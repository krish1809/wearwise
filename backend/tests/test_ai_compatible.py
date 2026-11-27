"""The real model provider (app/adapters/ai/compatible.py): what goes out in the
OpenAI-compatible request, what's read back, and what a busy free tier or a broken answer
becomes. The provider itself is replaced by canned answers; the shape is what matters."""

import io
import json
import urllib.error
from http.client import HTTPMessage
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_stylist import SEND

from app.adapters.ai import AIUnavailable, Message, ToolCall, ToolResult, ToolSpec
from app.adapters.ai.compatible import CompatibleProvider
from app.adapters.ai.fake import FakeAI

SEARCH = ToolSpec("search_wardrobe", "Find items.", {"type": "object", "properties": {}})
REPLY = ToolSpec("reply", "Answer.", {"type": "object", "properties": {}})
# Gemini's thought signature arrives like this, beside the call, and has to go back with it.
SIGNED = {"extra_content": {"google": {"thought_signature": "c2lnbmVk"}}}


class Answer(io.BytesIO):
    def __enter__(self) -> Answer:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def serve(monkeypatch: pytest.MonkeyPatch, *answers: object) -> list[Any]:
    """Make urlopen give these answers in turn: a dict (as JSON) or an exception. Returns the
    requests sent."""
    sent: list[Any] = []
    queue = list(answers)

    def urlopen(request: Any, timeout: float) -> Answer:
        sent.append(request)
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return Answer(json.dumps(answer).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return sent


def body(request: Any) -> dict[str, Any]:
    found: dict[str, Any] = json.loads(request.data)
    return found


def said(message: dict[str, Any], usage: tuple[int, int] = (300, 40)) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", **message}}],
        "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]},
    }


def error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    headers = HTTPMessage()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("u", code, "error", headers, None)


def provider() -> CompatibleProvider:
    return CompatibleProvider("https://models.example.com/v1/", "test-key", "chat-m", "vision-m")


def test_a_conversation_goes_out_in_the_compatible_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = serve(monkeypatch, said({"content": "Done."}))
    looked = ToolCall("call-7", "search_wardrobe", {"slot": "top"}, SIGNED)

    provider().chat(
        "You are a stylist.",
        [
            Message("user", "What tops do I have?"),
            Message("assistant", "Looking.", (looked,)),
            Message(
                "user",
                tool_results=(
                    ToolResult("call-7", '{"items": []}'),
                    ToolResult("call-8", "No such tool.", is_error=True),
                ),
            ),
        ],
        [SEARCH, REPLY],
    )

    [request] = sent
    assert request.full_url == "https://models.example.com/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer test-key"
    out = body(request)
    assert out["model"] == "chat-m"
    assert out["messages"] == [
        {"role": "system", "content": "You are a stylist."},
        {"role": "user", "content": "What tops do I have?"},
        {
            "role": "assistant",
            "content": "Looking.",
            "tool_calls": [
                {
                    **SIGNED,
                    "id": "call-7",
                    "type": "function",
                    "function": {"name": "search_wardrobe", "arguments": '{"slot": "top"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-7", "content": '{"items": []}'},
        {"role": "tool", "tool_call_id": "call-8", "content": "Error: No such tool."},
    ]
    assert [t["function"]["name"] for t in out["tools"]] == ["search_wardrobe", "reply"]
    assert out["tools"][0]["function"]["parameters"] == SEARCH.parameters
    assert out["tool_choice"] == "auto"


def test_the_answer_is_read_into_text_tool_calls_and_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    serve(
        monkeypatch,
        said(
            {
                "content": "Here goes.",
                "tool_calls": [
                    {
                        **SIGNED,
                        "id": "fc-1",
                        "type": "function",
                        "function": {"name": "search_wardrobe", "arguments": '{"slot": "top"}'},
                    },
                    # Some providers leave out the id, or the arguments when there are none.
                    {"type": "function", "function": {"name": "reply"}},
                ],
            }
        ),
    )

    turn = provider().chat("s", [Message("user", "Hi")], [SEARCH, REPLY])

    assert turn.text == "Here goes."
    first, second = turn.tool_calls
    assert (first.id, first.name, first.arguments, first.extra) == (
        "fc-1",
        "search_wardrobe",
        {"slot": "top"},
        SIGNED,
    )
    assert (second.id, second.name, second.arguments) == ("call-1", "reply", {})
    assert (turn.usage.input_tokens, turn.usage.output_tokens) == (300, 40)


def test_a_required_tool_is_the_only_one_offered(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = serve(monkeypatch, said({"content": None, "tool_calls": []}))

    turn = provider().chat("s", [Message("user", "Hi")], [SEARCH, REPLY], require="reply")

    out = body(sent[0])
    assert [t["function"]["name"] for t in out["tools"]] == ["reply"]
    assert out["tool_choice"] == "required"
    assert turn.text == "" and turn.tool_calls == ()


def test_a_photo_goes_as_a_data_url_and_its_description_comes_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    described = {
        "type": "function",
        "id": "t-1",
        "function": {"name": "describe_item", "arguments": '{"category_id": "shirt"}'},
    }
    sent = serve(monkeypatch, said({"tool_calls": [described]}, (900, 30)))
    schema = {"type": "object", "properties": {"category_id": {"enum": ["shirt"]}}}

    tagged = provider().tag_image(b"\x00\x01", "image/webp", schema, "Describe it.")

    out = body(sent[0])
    assert out["model"] == "vision-m"
    assert out["tool_choice"] == "required"
    assert out["tools"][0]["function"]["parameters"] == schema
    [message] = out["messages"]
    assert message["content"] == [
        {"type": "image_url", "image_url": {"url": "data:image/webp;base64,AAE="}},
        {"type": "text", "text": "Describe it."},
    ]
    assert tagged.fields == {"category_id": "shirt"}
    assert (tagged.usage.input_tokens, tagged.usage.output_tokens) == (900, 30)


def test_a_busy_free_tier_is_waited_for_once(monkeypatch: pytest.MonkeyPatch) -> None:
    waited: list[float] = []
    monkeypatch.setattr("app.adapters.ai.compatible.time.sleep", waited.append)
    sent = serve(monkeypatch, error(429, "3"), said({"content": "Hello."}))

    assert provider().chat("s", [Message("user", "Hi")], []).text == "Hello."
    assert len(sent) == 2 and waited == [3.0]


@pytest.mark.parametrize(
    ("answers", "reason", "tries"),
    [
        # Still busy after the wait.
        ([error(429), error(429)], "busy", 2),
        # A wait that long means the day's free requests are used up: not worth holding on.
        ([error(429, "3600")], "busy", 1),
        ([error(401)], "refused", 1),
        ([error(503), error(503)], "down", 2),
        ([TimeoutError("slow"), TimeoutError("slow")], "down", 2),
    ],
)
def test_what_a_failed_request_becomes(
    monkeypatch: pytest.MonkeyPatch, answers: list[Exception], reason: str, tries: int
) -> None:
    monkeypatch.setattr("app.adapters.ai.compatible.time.sleep", lambda seconds: None)
    sent = serve(monkeypatch, *answers)

    with pytest.raises(AIUnavailable) as raised:
        provider().chat("s", [Message("user", "Hi")], [])

    assert raised.value.reason == reason and len(sent) == tries


@pytest.mark.parametrize(
    "answer",
    [
        {"choices": []},
        said({"tool_calls": [{"function": {"name": "reply", "arguments": "{not json"}}]}),
        said({"tool_calls": [{"function": {"name": "reply", "arguments": "[1, 2]"}}]}),
    ],
)
def test_an_unreadable_answer_is_no_answer(
    monkeypatch: pytest.MonkeyPatch, answer: dict[str, Any]
) -> None:
    serve(monkeypatch, answer)

    with pytest.raises(AIUnavailable, match="no_answer"):
        provider().chat("s", [Message("user", "Hi")], [REPLY])


def test_a_photo_without_a_description_is_no_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch, said({"content": "It's a shirt."}))

    with pytest.raises(AIUnavailable, match="no_answer"):
        provider().tag_image(b"\x00", "image/webp", {"type": "object"}, "Describe it.")


def test_a_stylist_at_the_free_limit_says_so(sam: TestClient, ai: FakeAI) -> None:
    ai.turns = [AIUnavailable("busy")]

    sent = sam.post(SEND, json={"text": "What should I wear?"})

    assert sent.status_code == 503
    assert sent.json()["error"]["code"] == "ai_busy"
    assert "limit" in sent.json()["error"]["message"]
