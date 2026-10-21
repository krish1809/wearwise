"""The agents (docs/AGENTS.md): the Trend Scout, the weekly digest, and the stylist, as LangGraph
graphs (D55).

Agents decide what to look at, which tools to call, and how to word things; the engine and the
purchase analyzer decide what matches and what is worth buying. Agents reach the app's data only
through services, never through `api/`, and nothing in `services/` or `engine/` imports them.
"""
