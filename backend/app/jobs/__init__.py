"""Scheduled entry points (docs/AGENTS.md, section 6), run by GitHub Actions or by hand:
`python -m app.jobs.<name>`. Each takes its kind's "running" row in agent_runs first, so two
can't overlap, and records how it ended."""
