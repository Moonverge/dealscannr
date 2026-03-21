"""Rough per-scan cost estimate for observability."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

COST_PER_1K_TOKENS: dict[str, float] = {
    "groq/llama-3.1-70b": 0.00059,
    "groq/default": 0.00059,
    "openai/text-embedding-3-small": 0.00002,
    "together/bge-large": 0.00010,
    "nomic-embed": 0.00008,
}


def estimate_scan_cost(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    embedding_tokens: int,
    embedding_model_key: str,
) -> float:
    llm_rate = COST_PER_1K_TOKENS.get("groq/default", 0.00059)
    llm_cost = (prompt_tokens + completion_tokens) / 1000.0 * llm_rate
    embed_rate = COST_PER_1K_TOKENS.get(embedding_model_key, 0.0001)
    embed_cost = embedding_tokens / 1000.0 * embed_rate
    return round(llm_cost + embed_cost, 6)


def cost_meta_for_scan(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    embedding_tokens: int,
    embedding_model_key: str,
) -> dict[str, Any]:
    cost = estimate_scan_cost(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        embedding_tokens=embedding_tokens,
        embedding_model_key=embedding_model_key,
    )
    return {
        "estimated_cost_usd": cost,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "embedding_tokens": embedding_tokens,
    }


def log_cost_alert(scan_id: str, cost: float, threshold: float = 0.5) -> None:
    if cost > threshold:
        logger.warning(
            "scan_cost_alert scan_id=%s cost=%s threshold=%s",
            scan_id,
            cost,
            threshold,
        )
