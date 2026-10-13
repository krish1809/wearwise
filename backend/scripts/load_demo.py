"""Fill a demo account with a wardrobe of generic staples from seed/archetypes.json.

The account is marked as a demo, and the app labels it so. Running the script again replaces
the demo wardrobe. It refuses to change any account that isn't a demo account.

Usage:
  uv run python -m scripts.load_demo                       # demo@example.com, both sections
  uv run python -m scripts.load_demo --email demo2@example.com --section womenswear

A new demo account gets a random password, printed once.
"""

import argparse
import sys

from app.adapters.storage import get_storage
from app.core.db import get_sessionmaker
from app.services.demo import NotADemoAccount, load_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Load a demo wardrobe into a demo account.")
    parser.add_argument("--email", default="demo@example.com")
    parser.add_argument("--section", choices=["menswear", "womenswear", "both"], default="both")
    args = parser.parse_args()

    with get_sessionmaker()() as db:
        try:
            loaded = load_demo(db, args.email, args.section)
        except NotADemoAccount:
            sys.exit(f"{args.email} is a real account. This script only changes demo accounts.")
        db.commit()
    get_storage().delete(loaded.stale_keys)

    print(f"Demo wardrobe loaded: {loaded.items} items for {args.email}.")
    if loaded.password:
        print(f"Password (shown once): {loaded.password}")


if __name__ == "__main__":
    main()
