"""The real provider: Anthropic's Messages API over HTTPS, with Python's own HTTP client.

Its commercial terms say customer content isn't used to train models (checked October
2026), which matters for wardrobe photos. A timeout, and one retry when the service is busy
or erring; anything else is AIUnavailable, and the callers fall back.
"""

import base64
import json
import logging
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any

from app.adapters.ai import AIUnavailable, ChatTurn, Message, Tagged, ToolCall, ToolSpec, Usage

log = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
TIMEOUT_SECONDS = 30
ATTEMPTS = 2
MAX_TOKENS = 1500
RETRY_STATUSES = {429, 500, 502, 503, 504, 529}


class AnthropicProvider:
    def __init__(self, key: str, chat_model: str, vision_model: str) -> None:
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
        body: dict[str, Any] = {
            "model": self._chat_model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [_message(message) for message in messages],
            "tools": [
                {"name": t.name, "description": t.description, "input_schema": t.parameters}
                for t in tools
            ],
        }
        if require:
            body["tool_choice"] = {"type": "tool", "name": require}
        data = self._post(body)
        blocks = data.get("content") or []
        return ChatTurn(
            text="".join(b.get("text", "") for b in blocks if b.get("type") == "text"),
            tool_calls=tuple(
                ToolCall(str(b["id"]), str(b["name"]), dict(b.get("input") or {}))
                for b in blocks
                if b.get("type") == "tool_use"
            ),
            usage=_usage(data),
        )

    def tag_image(
        self, image: bytes, media_type: str, schema: dict[str, Any], instructions: str
    ) -> Tagged:
        data = self._post(
            {
                "model": self._vision_model,
                "max_tokens": 512,
                "tools": [
                    {
                        "name": "describe_item",
                        "description": "Describe the one garment or accessory in the photo.",
                        "input_schema": schema,
                    }
                ],
                "tool_choice": {"type": "tool", "name": "describe_item"},
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64.b64encode(image).decode("ascii"),
                                },
                            },
                            {"type": "text", "text": instructions},
                        ],
                    }
                ],
            }
        )
        for block in data.get("content") or []:
            if block.get("type") == "tool_use":
                return Tagged(dict(block.get("input") or {}), _usage(data))
        raise AIUnavailable("no_answer")

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode()
        for attempt in range(ATTEMPTS):
            request = urllib.request.Request(
                API_URL,
                data=payload,
                method="POST",
                headers={
                    "x-api-key": self._key,
                    "anthropic-version": API_VERSION,
                    "content-type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    data: dict[str, Any] = json.loads(response.read())
                    return data
            except urllib.error.HTTPError as error:
                log.warning("AI provider answered %s", error.code)
                if error.code not in RETRY_STATUSES or attempt == ATTEMPTS - 1:
                    raise AIUnavailable("refused" if error.code < 500 else "down") from error
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                log.warning("AI provider unreachable: %s", error)
                if attempt == ATTEMPTS - 1:
                    raise AIUnavailable("down") from error
        raise AIUnavailable("down")  # pragma: no cover


def _message(message: Message) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for result in message.tool_results:
        content.append(
            {
                "type": "tool_result",
                "tool_use_id": result.call_id,
                "content": result.content,
                "is_error": result.is_error,
            }
        )
    if message.text:
        content.append({"type": "text", "text": message.text})
    for call in message.tool_calls:
        content.append(
            {"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments}
        )
    return {"role": message.role, "content": content}


def _usage(data: dict[str, Any]) -> Usage:
    usage = data.get("usage") or {}
    return Usage(int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))
