from typing import Any


def rerank(chunks: list[dict[str, Any]], top_k: int = 8) -> list[dict[str, Any]]:
    """Keep top_k by score; no cross-encoder for MVP."""
    sorted_chunks = sorted(
        chunks,
        key=lambda c: c.get("score") or c.get("score", 0.0),
        reverse=True,
    )
    return sorted_chunks[:top_k]
