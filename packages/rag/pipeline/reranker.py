"""Reranker chain: Cohere → Jina API → FlashRank local (guaranteed floor)."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _extract_text(chunk: dict[str, Any]) -> str:
    p = chunk.get("payload") or chunk
    return str(p.get("normalized_text") or p.get("raw_text") or p.get("text") or "").strip()


def _cohere_rerank(chunks: list[dict], query: str, top_k: int) -> list[dict]:
    import cohere

    key = os.environ.get("COHERE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no cohere key")
    client = cohere.ClientV2(api_key=key)
    docs = [_extract_text(c) for c in chunks]
    if not docs:
        return []
    resp = client.rerank(model="rerank-v3.5", query=query, documents=docs, top_n=top_k)
    return [chunks[r.index] for r in resp.results if r.index < len(chunks)]


def _jina_rerank(chunks: list[dict], query: str, top_k: int) -> list[dict]:
    import httpx

    key = os.environ.get("JINA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no jina key")
    docs = [_extract_text(c) for c in chunks]
    if not docs:
        return []
    resp = httpx.post(
        "https://api.jina.ai/v1/rerank",
        json={
            "model": "jina-reranker-v2-base-multilingual",
            "query": query,
            "documents": docs,
            "top_n": top_k,
        },
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=10.0,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    ranked = sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)
    return [chunks[r["index"]] for r in ranked[:top_k] if r["index"] < len(chunks)]


def _flashrank_rerank(chunks: list[dict], query: str, top_k: int) -> list[dict]:
    from flashrank import Ranker, RerankRequest

    ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank_cache")
    docs = [_extract_text(c) for c in chunks]
    if not docs:
        return []
    passages = [{"id": i, "text": d} for i, d in enumerate(docs)]
    req = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(req)
    indices = [int(r["id"]) for r in results[:top_k]]
    return [chunks[i] for i in indices if i < len(chunks)]


def _score_sort(chunks: list[dict], top_k: int) -> list[dict]:
    return sorted(chunks, key=lambda c: c.get("score", 0.0), reverse=True)[:top_k]


def rerank(
    chunks: list[dict[str, Any]],
    top_k: int = 8,
    query: str = "",
) -> list[dict[str, Any]]:
    """Rerank with silent fallback: Cohere → Jina → FlashRank → score sort."""
    if not chunks:
        return []
    if not query:
        return _score_sort(chunks, top_k)

    try:
        result = _cohere_rerank(chunks, query, top_k)
        if result:
            logger.info("rerank_provider=cohere count=%d", len(result))
            return result
    except Exception as e:
        logger.warning("cohere_rerank_fallthrough: %s", type(e).__name__)

    try:
        result = _jina_rerank(chunks, query, top_k)
        if result:
            logger.info("rerank_provider=jina count=%d", len(result))
            return result
    except Exception as e:
        logger.warning("jina_rerank_fallthrough: %s", type(e).__name__)

    try:
        result = _flashrank_rerank(chunks, query, top_k)
        if result:
            logger.info("rerank_provider=flashrank count=%d", len(result))
            return result
    except Exception as e:
        logger.warning("flashrank_rerank_fallthrough: %s", type(e).__name__)

    return _score_sort(chunks, top_k)
