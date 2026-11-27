"""Create or update the agents' checkpoint tables (app/agents/checkpoint.py; D59).

The checkpointer's library owns these tables and versions them itself, building indexes
concurrently, which can't run inside a migration. So this runs after the migrations, on every
deploy and before every scheduled job. Safe to run any number of times. Like a migration, a
failure stops the start.

Usage:
  uv run python -m scripts.agent_setup
"""

from app.agents.checkpoint import setup


def main() -> None:
    setup()
    print("Agent checkpoint tables are ready.")


if __name__ == "__main__":
    main()
