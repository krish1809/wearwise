"""Load the reference lists in seed/ (colours, occasions, style profiles...) into the database.

Runs after migrations in `make migrate` and on every deploy; running it again changes nothing.

Usage: uv run python -m scripts.seed_reference
"""

from app.core.db import get_sessionmaker
from app.services.reference_seed import seed_reference_data


def main() -> None:
    with get_sessionmaker()() as db:
        changed = seed_reference_data(db)
    summary = ", ".join(f"{table} {count}" for table, count in changed.items())
    print(f"Reference data loaded. Rows added or changed: {summary}")


if __name__ == "__main__":
    main()
