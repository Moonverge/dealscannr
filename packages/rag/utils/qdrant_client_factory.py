"""Shared Qdrant client construction (Qdrant Cloud requires api_key)."""

from __future__ import annotations

from qdrant_client import QdrantClient


def qdrant_client(url: str, api_key: str | None = None) -> QdrantClient:
    u = url.rstrip("/")
    key = (api_key or "").strip() or None
    if key:
        return QdrantClient(url=u, api_key=key, check_compatibility=False)
    return QdrantClient(url=u, check_compatibility=False)
