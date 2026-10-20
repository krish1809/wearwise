"""The language model behind the stylist chat and photo tagging (docs/AI.md).

One interface, three settings: the real provider (anthropic.py), a fake with scripted
replies for tests (fake.py), and none at all (AI_PROVIDER=off), when the features say
they're unavailable and everything else works. Nothing about a vendor leaks out of this
package: the rest of the app sees plain messages, tool calls, and token counts.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, Protocol

from app.core.config import get_settings


class AIUnavailable(Exception):
    """The provider didn't answer, refused, or answered with something unusable."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    # A JSON schema for the arguments.
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ChatTurn:
    text: str
    tool_calls: tuple[ToolCall, ...]
    usage: Usage


@dataclass(frozen=True)
class Tagged:
    fields: dict[str, Any]
    usage: Usage


class AIProvider(Protocol):
    def chat(
        self,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        require: str | None = None,
    ) -> ChatTurn:
        """The model's next turn: text, tool calls, or both. With `require`, it must call
        that tool."""
        ...

    def tag_image(
        self, image: bytes, media_type: str, schema: dict[str, Any], instructions: str
    ) -> Tagged:
        """Fields describing the garment in the image, shaped by `schema`."""
        ...


@lru_cache
def get_ai() -> AIProvider | None:
    settings = get_settings()
    if settings.ai_provider == "fake":
        from app.adapters.ai.fake import FakeAI

        return FakeAI()
    if settings.ai_provider == "anthropic":
        from app.adapters.ai.anthropic import AnthropicProvider

        return AnthropicProvider(
            key=settings.ai_api_key or "",
            chat_model=settings.ai_model_chat or "",
            vision_model=settings.ai_model_vision or "",
        )
    return None
