import logging
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger()
_pylog = logging.getLogger(__name__)


def _status_to_error_code(status: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        402: "credits_exhausted",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_error",
    }.get(status, "http_error")


def install_error_handler(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail and "message" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        message = str(detail) if detail is not None else "Request failed"
        code = _status_to_error_code(exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": code, "message": message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors: Any = exc.errors()
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "detail": errors,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        _pylog.exception(
            "unhandled_exception path=%s error=%s",
            request.url.path,
            str(exc),
        )
        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )
