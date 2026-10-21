"""A chat model that answers from a script, for tests and for working offline
(AI_PROVIDER=fake, which production refuses).

Tests put replies in `script`, in order: plain text, tool calls, or the call that structured
output turns into an object. It remembers what it was sent and which tools it was offered, so a
test can check, for example, that no email address ever reached the model. With an empty
script it gives one honest reply, which structured output can't parse, so callers take their
fallback. `down` makes every call fail, as the real provider does when it's unreachable.
"""

from collections.abc import Callable, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field

REPLY = "A test reply from the fake model."
# Counted for every reply that doesn't set its own, so cost accounting can be tested.
USAGE = UsageMetadata(input_tokens=100, output_tokens=20, total_tokens=120)


class ModelDown(ConnectionError):
    """What the fake raises when `down`: like a provider that can't be reached."""


class ScriptedChatModel(BaseChatModel):
    script: list[AIMessage] = Field(default_factory=list)
    sent: list[list[BaseMessage]] = Field(default_factory=list)
    offered: list[list[str]] = Field(default_factory=list)
    down: bool = False

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.sent.append(list(messages))
        if self.down:
            raise ModelDown("the scripted model is down")
        reply = self.script.pop(0) if self.script else AIMessage(content=REPLY)
        if reply.usage_metadata is None:
            reply = reply.model_copy(update={"usage_metadata": USAGE})
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        self.offered.append([convert_to_openai_tool(tool)["function"]["name"] for tool in tools])
        return self


def tool_call(name: str, args: dict[str, Any], call_id: str = "call-1") -> AIMessage:
    """A scripted reply that calls one tool, or fills one structured-output schema (whose tool
    name is the schema's class name)."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])
