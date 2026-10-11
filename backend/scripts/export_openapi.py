"""Write the API's OpenAPI schema to a file, so the frontend's types can be generated from it.

Usage: uv run python -m scripts.export_openapi ../frontend/lib/api/openapi.json
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m scripts.export_openapi <output.json>")
    output = Path(sys.argv[1])
    output.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
