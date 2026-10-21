"""Tracing of agent runs (docs/AGENTS.md, section 2), off unless AGENT_TRACING says otherwise.

A tracing service receives the prompts. The stylist's and the digest's carry wardrobe data, so
in production only the Trend Scout, whose prompts hold nothing personal, may be traced. Every
run is switched explicitly, on or off, so a tracing variable set on the host by accident
can't turn it on.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from langsmith import Client, tracing_context

from app.core.config import get_settings

PROJECT = "wearwise"
# The one agent whose prompts carry nothing personal.
TRACEABLE_IN_PRODUCTION = {"trend_scout"}


def allowed(kind: str) -> bool:
    settings = get_settings()
    if settings.agent_tracing != "langsmith":
        return False
    return kind in TRACEABLE_IN_PRODUCTION or not settings.is_production


@contextmanager
def traced(kind: str) -> Iterator[None]:
    """Run an agent inside this: traced if allowed for its kind, explicitly untraced if not."""
    if not allowed(kind):
        with tracing_context(enabled=False):
            yield
        return
    client = Client(api_key=get_settings().langsmith_api_key)
    with tracing_context(enabled=True, project_name=PROJECT, client=client, tags=[kind]):
        yield
