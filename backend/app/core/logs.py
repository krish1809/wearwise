"""Logs: one JSON object per line in production, so the host's log search can filter by any
field, and readable lines in development. Every line written during a request carries that
request's id, which the browser also sent and the person sees on an error."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def _fields(record: logging.LogRecord) -> dict[str, Any]:
    fields: dict[str, Any] = getattr(record, "fields", {})
    current = request_id.get()
    return {"request_id": current, **fields} if current else dict(fields)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            **_fields(record),
        }
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = " ".join(f"{key}={value}" for key, value in _fields(record).items())
        line = f"{record.levelname:<7} {record.name}: {record.getMessage()} {fields}".rstrip()
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class _Ours(logging.StreamHandler):  # type: ignore[type-arg]
    """Marks the handler this module added, so configuring twice doesn't add a second."""


def configure_logging(production: bool) -> None:
    root = logging.getLogger()
    if not any(isinstance(handler, _Ours) for handler in root.handlers):
        handler = _Ours(sys.stdout)
        handler.setFormatter(JsonFormatter() if production else TextFormatter())
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    # The app writes its own line per request (app.api.middleware), without the query string
    # or the visitor's IP address; uvicorn's own would include both.
    logging.getLogger("uvicorn.access").disabled = True
