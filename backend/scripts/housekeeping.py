"""Remove what has expired: visitors' demo accounts over a day old, photos never saved, old
error reports and rate-limit counts, ended sessions, and agent checkpoints left behind
(app/services/housekeeping.py).

Runs before the server starts on Render. It never stops the start: a failure is printed and
the server starts anyway, and the next start tries again.

Usage:
  uv run python -m scripts.housekeeping
"""

from datetime import UTC, datetime

from app.adapters.storage import get_storage
from app.core.db import get_sessionmaker
from app.services.housekeeping import tidy


def main() -> None:
    try:
        with get_sessionmaker()() as db:
            counts, keys = tidy(db, datetime.now(UTC))
            db.commit()
        get_storage().delete(keys)
    except Exception as error:
        print(f"Housekeeping skipped: {type(error).__name__}: {error}")
        return
    print("Housekeeping: " + ", ".join(f"{count} {name}" for name, count in counts.items()) + ".")


if __name__ == "__main__":
    main()
