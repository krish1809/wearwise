"""The chat model the agents call (D55): LangChain's integration for the provider in the
settings (the same AI_PROVIDER, key, and model as the stylist in M10), the scripted fake, or
None when AI is off.

Every call is counted against the same daily spend cap as the stylist (app/services/ai_usage.py),
from the token counts the model reports.
"""

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from app.adapters.ai import Usage
from app.core.config import get_settings

TIMEOUT_SECONDS = 30
MAX_TOKENS = 2000


@lru_cache
def get_chat_model() -> BaseChatModel | None:
    settings = get_settings()
    if settings.ai_provider == "fake":
        from app.agents.fake import ScriptedChatModel

        return ScriptedChatModel()
    if settings.ai_provider == "anthropic":
        # One retry when the provider is busy, as in M10; the agents fall back after that.
        return init_chat_model(
            settings.ai_model_chat or "",
            model_provider="anthropic",
            api_key=settings.ai_api_key,
            timeout=TIMEOUT_SECONDS,
            max_retries=1,
            max_tokens=MAX_TOKENS,
        )
    return None


def usage(message: AIMessage) -> Usage:
    """The tokens one reply took, as the rest of the app counts them."""
    found = message.usage_metadata
    if found is None:
        return Usage(0, 0)
    return Usage(found["input_tokens"], found["output_tokens"])
