"""Sentence-window chunking for long connector output (no heavy deps)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.connectors.base import RawChunk

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
MAX_CHUNK_CHARS = 2048  # ~512 tokens
WINDOW_SIZE = 3

CHUNKABLE_CONNECTORS = frozenset({
    "sec_edgar", "courtlistener", "news_connector", "wikipedia",
})


def should_chunk(connector_id: str, text: str) -> bool:
    return connector_id in CHUNKABLE_CONNECTORS and len(text) > MAX_CHUNK_CHARS


def sentence_window_chunk(
    text: str,
    window: int = WINDOW_SIZE,
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[str]:
    sentences = SENTENCE_SPLIT.split(text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences or len(sentences) <= window:
        return [text[:max_chars]]
    chunks: list[str] = []
    step = max(1, window - 1)
    for i in range(0, len(sentences), step):
        chunk = " ".join(sentences[i : i + window])[:max_chars]
        chunks.append(chunk)
        if i + window >= len(sentences):
            break
    return chunks or [text[:max_chars]]


def apply_semantic_chunking(raw_chunks: list[RawChunk]) -> list[RawChunk]:
    """Split long chunks from prose-heavy connectors into overlapping sentence windows."""
    from rag.connectors.base import RawChunk as RC

    out: list[RC] = []
    for ch in raw_chunks:
        if not should_chunk(ch.connector_id, ch.normalized_text):
            out.append(ch)
            continue
        windows = sentence_window_chunk(ch.normalized_text)
        for idx, window_text in enumerate(windows):
            out.append(
                RC(
                    source_url=ch.source_url,
                    raw_text=ch.raw_text if idx == 0 else window_text,
                    normalized_text=window_text,
                    retrieved_at=ch.retrieved_at,
                    connector_id=ch.connector_id,
                    entity_id=ch.entity_id,
                    scan_id=ch.scan_id,
                    metadata={**ch.metadata, "chunk_window": idx},
                )
            )
    return out
