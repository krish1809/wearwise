"""The real provider: any service that takes the OpenAI-compatible chat request (D60), over
HTTPS with Python's own HTTP client.

That request format is the one most model providers accept, free tiers included: Google's
Gemini API (the default in .env.example), Groq, Mistral, OpenRouter, or a model running on
your own machine with Ollama. Only AI_BASE_URL, the key, and the model names change; nothing
is sent to OpenAI itself. A timeout, and one retry when the service errs or asks to wait a few
seconds; anything else is AIUnavailable, and the callers fall back.
"""

import base64
import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any

from app.adapters.ai import AIUnavailable, ChatTurn, Message, Tagged, ToolCall, ToolSpec, Usage

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
ATTEMPTS = 2
# Some models think before they answer, and that counts towards this too.
MAX_TOKENS = 4000
RETRY_STATUSES = {429, 500, 502, 503, 504}
# A free tier answers 429 when its per-minute limit is reached. Worth waiting this long for the
# minute to roll over, and no longer: someone is waiting for the answer.
MAX_WAIT_SECONDS = 10
DEFAULT_WAIT_SECONDS = 2


class CompatibleProvider:
    def __init__(self, base_url: str, key: str, chat_model: str, vision_model: str) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._key = key
        self._chat_model = chat_model
        self._vision_model = vision_model

    def chat(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        require: str | None = None,
    ) -> ChatTurn:
        # A required tool is the only one offered, so "required" can mean only that one: the
        # named form of tool_choice isn't accepted everywhere.
        offered = [t for t in tools if t.name == require] if require else list(tools)
        body: dict[str, Any] = {
            "model": self._chat_model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "system", "content": system}]
            + [part for message in messages for part in _message(message)],
        }
        if offered:
            body["tools"] = [_tool(t) for t in offered]
            body["tool_choice"] = "required" if require else "auto"
        data = self._post(body)
        answer = _answer(data)
        return ChatTurn(
            text=answer.get("content") or "",
            tool_calls=tuple(_call(n, c) for n, c in enumerate(answer.get("tool_calls") or [])),
            usage=_usage(data),
        )

    def tag_image(
        self, image: bytes, media_type: str, schema: dict[str, Any], instructions: str
    ) -> Tagged:
        encoded = base64.b64encode(image).decode("ascii")
        data = self._post(
            {
                "model": self._vision_model,
                "max_tokens": MAX_TOKENS,
                "tools": [
                    _tool(
                        ToolSpec(
                            "describe_item",
                            "Describe the one garment or accessory in the photo.",
                            schema,
                        )
                    )
                ],
                "tool_choice": "required",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{encoded}"},
                            },
                            {"type": "text", "text": instructions},
                        ],
                    }
                ],
            }
        )
        for n, found in enumerate(_answer(data).get("tool_calls") or []):
            call = _call(n, found)
            if call.name == "describe_item":
                return Tagged(call.arguments, _usage(data))
        raise AIUnavailable("no_answer")

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode()
        for attempt in range(ATTEMPTS):
            request = urllib.request.Request(
                self._url,
                data=payload,
                method="POST",
                headers={
                    "authorization": f"Bearer {self._key}",
                    "content-type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    data: dict[str, Any] = json.loads(response.read())
                    return data
            except urllib.error.HTTPError as error:
                log.warning("AI provider answered %s", error.code)
                busy = error.code == 429
                wait = _wait(error) if busy else 0.0
                last = attempt == ATTEMPTS - 1
                if error.code not in RETRY_STATUSES or last or wait > MAX_WAIT_SECONDS:
                    reason = "busy" if busy else "refused" if error.code < 500 else "down"
                    raise AIUnavailable(reason) from error
                time.sleep(wait)
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                log.warning("AI provider unreachable: %s", error)
                if attempt == ATTEMPTS - 1:
                    raise AIUnavailable("down") from error
        raise AIUnavailable("down")  # pragma: no cover


def _wait(error: urllib.error.HTTPError) -> float:
    """How long a 429 asks to wait, in seconds; a short pause when it doesn't say."""
    said = error.headers.get("retry-after") if error.headers is not None else None
    try:
        return float(said or DEFAULT_WAIT_SECONDS)
    except ValueError:
        return DEFAULT_WAIT_SECONDS


def _tool(spec: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        },
    }


def _message(message: Message) -> list[dict[str, Any]]:
    """One message as the format has it: tool results are messages of their own."""
    parts: list[dict[str, Any]] = [
        {
            "role": "tool",
            "tool_call_id": result.call_id,
            "content": ("Error: " if result.is_error else "") + result.content,
        }
        for result in message.tool_results
    ]
    if message.role == "assistant":
        said: dict[str, Any] = {"role": "assistant", "content": message.text or None}
        if message.tool_calls:
            said["tool_calls"] = [
                {
                    **call.extra,
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                }
                for call in message.tool_calls
            ]
        parts.append(said)
    elif message.text:
        parts.append({"role": "user", "content": message.text})
    return parts


def _answer(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices") or []
    if not choices or not isinstance(choices[0].get("message"), dict):
        raise AIUnavailable("no_answer")
    answer: dict[str, Any] = choices[0]["message"]
    return answer


def _call(n: int, found: dict[str, Any]) -> ToolCall:
    function = found.get("function") or {}
    try:
        arguments = json.loads(function.get("arguments") or "{}")
    except ValueError as error:
        raise AIUnavailable("no_answer") from error
    if not isinstance(arguments, dict):
        raise AIUnavailable("no_answer")
    # Anything else the provider put on the call goes back with it unchanged.
    extra = {k: v for k, v in found.items() if k not in ("id", "type", "function")}
    return ToolCall(
        str(found.get("id") or f"call-{n}"), str(function.get("name", "")), arguments, extra
    )


def _usage(data: dict[str, Any]) -> Usage:
    usage = data.get("usage") or {}
    return Usage(int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)))
