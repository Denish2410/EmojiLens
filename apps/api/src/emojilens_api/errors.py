"""Structured error responses: ``{"error": {"code", "message", "details"}}``."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from emojilens_core.unicode import InvalidUnicodeError


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ApiError(Exception):
    def __init__(
        self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _response(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status, content=body.model_dump())


def _sanitize_validation_errors(errors: Any) -> list[dict[str, Any]]:
    # Never echo submitted input back in error payloads; keep location and type only.
    return [
        {"loc": list(e.get("loc", ())), "type": e.get("type"), "msg": e.get("msg")} for e in errors
    ]


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(InvalidUnicodeError)
    async def _invalid_unicode(_: Request, exc: InvalidUnicodeError) -> JSONResponse:
        details = exc.to_dict()
        return _response(
            422, exc.code, str(exc), {k: details[k] for k in ("codepoint_offset", "codepoint")}
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = _sanitize_validation_errors(exc.errors())
        if any(e["type"] == "string_unicode" for e in errors):
            return _response(422, "invalid_unicode", "Input is not well-formed Unicode.", errors)
        return _response(422, "validation_error", "Request validation failed.", errors)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return _response(exc.status_code, code, str(exc.detail))
