"""What wraps every request: an id, a log line, a record of anything that breaks, and the headers
every response carries. Written as plain ASGI middleware, so a streamed photo or download isn't
buffered on its way out."""

import json
import logging
import re
import time
import traceback
import uuid
from collections.abc import Callable
from functools import partial

from anyio import to_thread
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logs import request_id

log = logging.getLogger("app.requests")

# An id the browser sent is kept if it looks like one; otherwise the server makes its own.
REQUEST_ID = re.compile(r"[A-Za-z0-9-]{8,64}")

# The API sends JSON and images: nothing in a response should run, load, or be framed.
LOCKED_DOWN = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# The interactive API docs load their script and styles from a CDN, so they get no policy.
DOCS = ("/docs", "/redoc", "/openapi.json")

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cross-origin-resource-policy", b"same-origin"),
]


class SecurityHeaders:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        docs = str(scope["path"]).startswith(DOCS)

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                headers += [h for h in SECURITY_HEADERS if h[0] not in present]
                if not docs and b"content-security-policy" not in present:
                    headers.append((b"content-security-policy", LOCKED_DOWN.encode()))
                # Answers about a person's data aren't kept by browsers or anything between;
                # photos set their own (private) caching.
                if b"cache-control" not in present:
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, with_headers)


class RequestContext:
    """Gives each request an id (the browser's, if it sent a sensible one), logs one line when
    it ends, and turns an unexpected error into a recorded event and a 500 that names the id,
    so a person can quote it."""

    def __init__(self, app: ASGIApp, record: Callable[..., None] | None = None) -> None:
        self.app = app
        if record is None:
            from app.services.ops import record_server_error

            record = record_server_error
        self.record = record

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        sent = dict(scope.get("headers", [])).get(b"x-request-id", b"").decode("latin-1")
        rid = sent if REQUEST_ID.fullmatch(sent) else uuid.uuid4().hex[:16]
        token = request_id.set(rid)
        started = time.perf_counter()
        status = 500
        responded = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, responded
            if message["type"] == "http.response.start":
                responded = True
                status = message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-request-id", rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as error:
            log.exception("Unhandled error", extra={"fields": {"path": _route(scope)}})
            fields = {
                "request_id": rid,
                "method": scope["method"],
                "path": _route(scope),
                "status": 500,
                "kind": type(error).__name__,
                "message": str(error) or type(error).__name__,
                "detail": "".join(traceback.format_exception(error)),
            }
            await to_thread.run_sync(partial(self.record, **fields))
            if responded:
                raise
            status = 500
            await _server_error(send, rid)
        finally:
            log.info(
                "request",
                extra={
                    "fields": {
                        "method": scope["method"],
                        "path": _route(scope),
                        "status": status,
                        "ms": round((time.perf_counter() - started) * 1000),
                    }
                },
            )
            request_id.reset(token)


def _route(scope: Scope) -> str:
    """The path with each parameter's value replaced by its name, such as
    /api/v1/items/{item_id}, so logs group by route and hold no ids. Never the query string."""
    path = str(scope.get("path", ""))
    for name, value in (scope.get("path_params") or {}).items():
        path = path.replace(f"/{value}", f"/{{{name}}}", 1)
    return path


async def _server_error(send: Send, rid: str) -> None:
    message = (
        "Something went wrong on our side. Try again in a moment; if it keeps happening, "
        f"mention reference {rid}."
    )
    body = json.dumps({"error": {"code": "server_error", "message": message}}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"x-request-id", rid.encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
