"""Structured API error payloads (machine code + human message)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def raise_api_error(
    *,
    status_code: int,
    error: str,
    message: str,
    detail: Any = None,
) -> None:
    body: dict[str, Any] = {"error": error, "message": message}
    if detail is not None:
        body["detail"] = detail
    raise HTTPException(status_code=status_code, detail=body)
