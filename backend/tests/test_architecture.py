"""The layers stay apart. The engine is pure: it imports no web, database, adapter, or agent
code. Agents reach data through services, never through the web layer. Services know nothing
of the agents or the jobs that run them (docs/AGENTS.md, section 2)."""

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
FORBIDDEN = ("app.api", "app.models", "app.services", "app.adapters", "app.agents", "app.jobs")
# Each layer, and the parts of the app it must never import.
LAYERS = {
    "engine": FORBIDDEN,
    "agents": ("app.api", "app.jobs"),
    "services": ("app.api", "app.agents", "app.jobs"),
}


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


def is_forbidden(module: str, forbidden: tuple[str, ...] = FORBIDDEN) -> bool:
    return any(module == name or module.startswith(name + ".") for name in forbidden)


@pytest.mark.parametrize("layer", sorted(LAYERS))
def test_each_layer_imports_only_what_it_may(layer: str) -> None:
    files = sorted((APP_DIR / layer).rglob("*.py"))
    violations = []
    for path in files:
        package = ".".join(path.parent.relative_to(APP_DIR.parent).parts)
        violations += [
            f"{path.relative_to(APP_DIR.parent)} imports {module}"
            for module in sorted(imported_modules(path.read_text(), package))
            if is_forbidden(module, LAYERS[layer])
        ]

    assert files and violations == []


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
