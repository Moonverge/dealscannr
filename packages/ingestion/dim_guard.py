"""Qdrant collection vector dimension guard (ingestion + scan pipeline)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from qdrant_client import QdrantClient

from rag.utils.qdrant_client_factory import qdrant_client as _make_qdrant_client

logger = logging.getLogger(__name__)

COLLECTION_DEFAULT = "dealscannr_chunks"


def _vectors_size(params_vectors: Any) -> int:
    """Resolve single-vector size from Qdrant collection config."""
    if params_vectors is None:
        raise ValueError("collection has no vectors config")
    if isinstance(params_vectors, dict):
        if not params_vectors:
            raise ValueError("empty vectors dict")
        first = next(iter(params_vectors.values()))
        if hasattr(first, "size"):
            return int(first.size)
        if isinstance(first, dict) and "size" in first:
            return int(first["size"])
        raise ValueError("cannot read vector size from named vectors config")
    if hasattr(params_vectors, "size"):
        return int(params_vectors.size)
    raise ValueError("cannot read vector size from collection config")


def verify_collection_dim_sync(
    client: QdrantClient,
    collection_name: str,
    expected_dim: int,
) -> None:
    """
    Raises ValueError if collection exists and vector size != expected_dim.
    No-op if collection does not exist (will be created with correct dim).
    """
    try:
        info = client.get_collection(collection_name)
    except Exception as e:
        msg = str(e).lower()
        if (
            "not found" in msg
            or "doesn't exist" in msg
            or "does not exist" in msg
            or "404" in msg
            or "unknown collection" in msg
        ):
            logger.debug("dim_guard collection missing ok name=%s", collection_name)
            return
        raise
    existing_dim = _vectors_size(info.config.params.vectors)
    if existing_dim != expected_dim:
        raise ValueError(
            f"Embedding dimension mismatch: "
            f"collection has {existing_dim}d, "
            f"current provider produces {expected_dim}d. "
            f"Drop collection or switch provider. "
            f"Run: qdrant-client delete collection {collection_name}"
        )


def verify_collection_dim_for_url_sync(
    qdrant_url: str,
    collection_name: str,
    expected_dim: int,
    qdrant_api_key: str | None = None,
) -> None:
    client = _make_qdrant_client(qdrant_url, qdrant_api_key)
    verify_collection_dim_sync(client, collection_name, expected_dim)


async def verify_collection_dim(
    qdrant_url: str,
    collection_name: str,
    expected_dim: int,
    *,
    qdrant_api_key: str | None = None,
) -> None:
    """Async wrapper (runs sync Qdrant client in a thread)."""
    await asyncio.to_thread(
        verify_collection_dim_for_url_sync,
        qdrant_url,
        collection_name,
        expected_dim,
        qdrant_api_key,
    )


verify_collection_dim_async = verify_collection_dim
