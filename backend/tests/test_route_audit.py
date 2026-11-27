"""Checks that walk every route, so a new route can't quietly skip login, the CSRF header, or
the 404 for an id that isn't there."""

import re
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# The only routes anyone may call without logging in.
PUBLIC = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/demo"),
    ("POST", "/api/v1/client-errors"),
    # Links sent by email, which work without logging in: each is guarded by its token.
    ("POST", "/api/v1/auth/confirm-email"),
    ("POST", "/api/v1/auth/password-reset"),
    ("POST", "/api/v1/auth/password-reset/confirm"),
    ("POST", "/api/v1/email/unsubscribe"),
    ("POST", "/api/v1/email/not-for-me"),
    ("POST", "/api/v1/email/unsubscribe/one-click"),
}
# Changes that can't carry the custom header: a mail app's one-click unsubscribe button posts
# from the mail provider's servers (RFC 8058). Its signed token guards it instead (D57).
NO_HEADER = {("POST", "/api/v1/email/unsubscribe/one-click")}
STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}
# A floor, so the checks can't pass by walking nothing.
AT_LEAST = 90


def _routes(app: FastAPI) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Every operation in the schema: the list routers are actually served from."""
    for path, operations in app.openapi()["paths"].items():
        for method, operation in operations.items():
            yield method.upper(), path, operation


def _ids(operation: dict[str, Any]) -> set[str]:
    return {
        param["name"]
        for param in operation.get("parameters", [])
        if param["in"] == "path" and param["schema"].get("format") == "uuid"
    }


def _filled(path: str, operation: dict[str, Any]) -> str:
    """The path with every parameter filled in: a fresh UUID where one is expected, and the
    first allowed value for a fixed choice."""
    params = {p["name"]: p["schema"] for p in operation.get("parameters", []) if p["in"] == "path"}

    def value(name: str) -> str:
        schema = params.get(name, {})
        if schema.get("format") == "uuid":
            return str(uuid.uuid4())
        return str(schema.get("enum", ["x"])[0])

    return re.sub(r"\{(\w+)\}", lambda m: value(m.group(1)), path)


def test_the_checks_see_every_route(app: FastAPI) -> None:
    assert len(list(_routes(app))) >= AT_LEAST


def test_every_route_but_the_public_ones_needs_a_login(app: FastAPI, client: TestClient) -> None:
    open_routes = []
    for method, path, operation in _routes(app):
        if (method, path) in PUBLIC:
            continue
        response = client.request(method, _filled(path, operation))
        if response.status_code != 401:
            open_routes.append(f"{method} {path}: {response.status_code}")

    assert open_routes == []


def test_every_change_needs_the_csrf_header(app: FastAPI) -> None:
    unguarded = []
    with TestClient(app) as bare:
        for method, path, operation in _routes(app):
            if method not in STATE_CHANGING or (method, path) in NO_HEADER:
                continue
            response = bare.request(method, _filled(path, operation))
            if response.status_code != 403 or response.json()["error"]["code"] != "missing_header":
                unguarded.append(f"{method} {path}: {response.status_code}")

    assert unguarded == []


@pytest.mark.parametrize("method", ["GET", "DELETE"])
def test_an_id_that_isnt_there_is_404(app: FastAPI, sam: TestClient, method: str) -> None:
    """Someone else's id and a made-up one look the same: 404, never 500."""
    wrong = []
    for route_method, path, operation in _routes(app):
        if route_method != method or not _ids(operation):
            continue
        response = sam.request(method, _filled(path, operation))
        if response.status_code != 404:
            wrong.append(f"{method} {path}: {response.status_code}")

    assert wrong == []


def test_every_schema_has_a_name_of_its_own(app: FastAPI) -> None:
    """Two models with one name get long made-up names in the schema, which renames them in the
    frontend's generated types and breaks the code that uses them."""
    clashes = [name for name in app.openapi()["components"]["schemas"] if name.startswith("app__")]

    assert clashes == []
