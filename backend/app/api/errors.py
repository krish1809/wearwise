"""One shape for every error the API returns: {"error": {"code", "message", "fields"}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorDetail(BaseModel):
    code: str
    message: str
    # Per-field messages for forms, keyed by field name.
    fields: dict[str, str] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """Document which error statuses a route returns, so the frontend's types know the shape."""
    return {status: {"model": ErrorResponse} for status in statuses}


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = ErrorDetail(code=code, message=message, fields=fields)
        self.headers = headers


def _json(
    status_code: int, detail: ErrorDetail, headers: dict[str, str] | None = None
) -> JSONResponse:
    body = ErrorResponse(error=detail).model_dump(exclude_none=True)
    return JSONResponse(body, status_code=status_code, headers=headers)


def _field_message(error: dict[str, Any]) -> str:
    message = str(error.get("msg", "This value isn't valid."))
    # Our own validators raise ValueError("..."); Pydantic prefixes it.
    return message.removeprefix("Value error, ")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, error: ApiError) -> JSONResponse:
        return _json(error.status_code, error.detail, error.headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(_: Request, error: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for item in error.errors():
            location = [str(part) for part in item.get("loc", ()) if part != "body"]
            fields.setdefault(".".join(location) or "body", _field_message(item))
        detail = ErrorDetail(
            code="invalid_input", message="Check the highlighted fields.", fields=fields
        )
        return _json(422, detail)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
        codes = {404: "not_found", 405: "method_not_allowed"}
        detail = ErrorDetail(
            code=codes.get(error.status_code, "http_error"), message=str(error.detail)
        )
        return _json(error.status_code, detail, getattr(error, "headers", None))
