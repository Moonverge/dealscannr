"""Build labeled chunk blocks for LLM context with stable chunk_id rules."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


def _coerce_mapping(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    md = getattr(obj, "model_dump", None)
    if callable(md):
        try:
            out = md()
            if isinstance(out, dict):
                return out
        except Exception:
            pass
    try:
        return dict(obj)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return {}


def _payload_from_hit(hit: Any) -> dict[str, Any]:
    """
    Normalize Qdrant ScoredPoint-like objects, wrapped dict hits, or flat Mongo/Qdrant dicts.
    """
    if hasattr(hit, "payload"):
        return _coerce_mapping(getattr(hit, "payload"))
    if isinstance(hit, dict):
        inner = hit.get("payload")
        if inner is not None:
            coerced = _coerce_mapping(inner)
            if coerced:
                return coerced
        if hit.get("normalized_text") or hit.get("raw_text") or hit.get("text"):
            return hit
        return {}
    return {}


def deterministic_chunk_id(
    scan_id: str,
    connector_id: str,
    source_url: str,
    text_prefix: str,
) -> str:
    """16-char hex id when no Mongo chunk_id is stored yet."""
    basis = f"{scan_id}|{connector_id}|{source_url}|{text_prefix[:100]}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _format_block(
    chunk_id: str,
    source_url: str,
    retrieved_at: str,
    body: str,
) -> str:
    return (
        f"[chunk_id: {chunk_id}]\n"
        f"Source: {source_url} ({retrieved_at})\n"
        f"{body.strip()}"
    )


def chunk_id_from_qdrant_payload(
    payload: dict[str, Any],
    *,
    scan_id: str,
    connector_fallback: str,
    body: str,
) -> str:
    for key in ("chunk_id", "mongo_chunk_id", "_id"):
        raw = payload.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    url = str(payload.get("source_url") or "")
    conn = str(payload.get("connector_id") or connector_fallback)
    return deterministic_chunk_id(scan_id, conn, url, body)


def distinct_connector_count_from_hits(hits: list[Any]) -> int:
    """Count distinct connector_id values in Qdrant/Mongo-shaped retrieval hits."""
    if not hits:
        return 0
    seen: set[str] = set()
    for h in hits:
        p = _payload_from_hit(h)
        c = str(p.get("connector_id") or "").strip()
        seen.add(c or "unknown")
    return len(seen)


def labeled_blocks_from_qdrant_hits(
    hits: list[Any],
    *,
    scan_id: str,
    default_connector_id: str = "qdrant_index",
) -> tuple[str, list[str]]:
    """Returns (joined labeled context, ordered chunk_ids)."""
    blocks: list[str] = []
    ids: list[str] = []
    for hit in hits:
        payload = _payload_from_hit(hit)
        body = str(
            payload.get("normalized_text")
            or payload.get("raw_text")
            or "",
        ).strip()
        if not body and isinstance(hit, dict):
            body = str(
                hit.get("text")
                or hit.get("normalized_text")
                or hit.get("raw_text")
                or "",
            ).strip()
        if not body:
            continue
        source_url = str(payload.get("source_url") or "")
        retrieved_at = str(
            payload.get("retrieved_at")
            or payload.get("ingested_at")
            or "",
        )
        if not retrieved_at:
            retrieved_at = datetime.now(timezone.utc).isoformat()
        conn = str(payload.get("connector_id") or default_connector_id)
        cid = chunk_id_from_qdrant_payload(
            payload,
            scan_id=scan_id,
            connector_fallback=conn,
            body=body,
        )
        ids.append(cid)
        blocks.append(_format_block(cid, source_url, retrieved_at, body))
    return "\n\n".join(blocks), ids


def labeled_block_from_live_snapshot(
    live_body: str,
    live_urls: list[str],
    *,
    scan_id: str,
    connector_id: str = "live_web",
) -> tuple[str, list[str]]:
    """Single aggregated live snapshot with deterministic id (not yet persisted)."""
    text = (live_body or "").strip()
    if not text:
        return "", []
    primary_url = live_urls[0] if live_urls else "https://live-context.local/dealscannr"
    retrieved_at = datetime.now(timezone.utc).isoformat()
    cid = deterministic_chunk_id(scan_id, connector_id, primary_url, text)
    block = _format_block(cid, primary_url, retrieved_at, text)
    return block, [cid]


def labeled_block_from_empty_state(company_name: str, *, scan_id: str) -> tuple[str, list[str]]:
    """One synthetic block so the model has no valid excuses to invent chunk ids."""
    text = f"No indexed chunks and no live web snapshot retrieved for {company_name}."
    cid = deterministic_chunk_id(scan_id, "empty", "", text)
    block = _format_block(cid, "", datetime.now(timezone.utc).isoformat(), text)
    return block, [cid]
