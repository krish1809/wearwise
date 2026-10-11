"""The engine stays pure: it must not import the web, database, or adapter layers."""

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
FORBIDDEN = ("app.api", "app.models", "app.services", "app.adapters")


def imported_modules(source: str, package: str) -> set[str]:
    """Every module a file imports, with relative imports resolved against its package."""
    parts = package.split(".")
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = parts[: len(parts) - node.level + 1] if node.level else []
            target = ".".join([*base, node.module] if node.module else base)
            found.add(target)
            # `from app import models` imports a module by name, so check each name too.
            found.update(f"{target}.{alias.name}" for alias in node.names)
    return found


def is_forbidden(module: str) -> bool:
    return any(module == name or module.startswith(name + ".") for name in FORBIDDEN)


def test_engine_imports_nothing_from_the_app_layers() -> None:
    violations = []
    for path in sorted((APP_DIR / "engine").rglob("*.py")):
        package = ".".join(path.parent.relative_to(APP_DIR.parent).parts)
        violations += [
            f"{path.relative_to(APP_DIR.parent)} imports {module}"
            for module in sorted(imported_modules(path.read_text(), package))
            if is_forbidden(module)
        ]

    assert violations == []


@pytest.mark.parametrize(
    "source",
    [
        "import app.models",
        "from app.services.items import load_items",
        "from app import adapters",
        "from ..api import router",
    ],
)
def test_the_check_catches_every_import_form(source: str) -> None:
    assert any(is_forbidden(module) for module in imported_modules(source, "app.engine"))


def test_the_check_allows_the_engine_and_the_standard_library() -> None:
    source = "import math\nfrom .scoring import pair_score\nfrom app.engine import types"

    assert not any(is_forbidden(module) for module in imported_modules(source, "app.engine"))
