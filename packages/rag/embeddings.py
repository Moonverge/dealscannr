"""Embeddings for Qdrant: OpenAI (1536) > Together (varies) > Nomic (768). Groq is not used for embeddings."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from rag.connectors.http_client import safe_post_sync

logger = logging.getLogger(__name__)

OPENAI_EMBED_MODEL = "text-embedding-3-small"
OPENAI_VECTOR_DIM = 1536
TOGETHER_BASE_URL = "https://api.together.xyz/v1"
TOGETHER_DEFAULT_EMBED_MODEL = "BAAI/bge-large-en-v1.5"
# Known output sizes for Together serverless embedding models (override with TOGETHER_EMBEDDING_DIM if yours differs).
_TOGETHER_MODEL_DIMS: dict[str, int] = {
    "BAAI/bge-large-en-v1.5": 1024,
    "WhereIsAI/UAE-Large-V1": 1024,
    "intfloat/multilingual-e5-large-instruct": 1024,
    "togethercomputer/m2-bert-80M-8k-retrieval": 768,
}
NOMIC_EMBED_MODEL = "nomic-embed-text-v1.5"
NOMIC_EMBED_URL = "https://api-atlas.nomic.ai/v1/embedding/text"
NOMIC_VECTOR_DIM = 768


def _together_embed_model() -> str:
    return (os.environ.get("TOGETHER_EMBEDDING_MODEL") or "").strip() or TOGETHER_DEFAULT_EMBED_MODEL


def _resolved_embedding_keys(
    *,
    openai_api_key: str | None = None,
    together_api_key: str | None = None,
    nomic_api_key: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Prefer explicit args; fall back to process env (covers uvicorn cwd / dotenv edge cases)."""
    oai = (openai_api_key or "").strip() or (os.environ.get("OPENAI_API_KEY") or "").strip() or None
    tog = (together_api_key or "").strip() or (os.environ.get("TOGETHER_API_KEY") or "").strip() or None
    nom = (nomic_api_key or "").strip() or (os.environ.get("NOMIC_API_KEY") or "").strip() or None
    return oai, tog, nom


def together_vector_dim() -> int:
    m = _together_embed_model()
    if m in _TOGETHER_MODEL_DIMS:
        return _TOGETHER_MODEL_DIMS[m]
    raw = (os.environ.get("TOGETHER_EMBEDDING_DIM") or "").strip()
    if raw.isdigit():
        return int(raw)
    return 1024


def get_active_embedding_dim(settings: Any) -> int | None:
    """Expected vector size for the first configured embedding provider (OpenAI > Together > Nomic)."""
    oai, tog, nom = _resolved_embedding_keys(
        openai_api_key=getattr(settings, "openai_api_key", None),
        together_api_key=getattr(settings, "together_api_key", None),
        nomic_api_key=getattr(settings, "nomic_api_key", None),
    )
    if oai:
        return OPENAI_VECTOR_DIM
    if tog:
        return together_vector_dim()
    if nom:
        return NOMIC_VECTOR_DIM
    return None


def embedding_vector_dim(
    openai_api_key: str | None,
    together_api_key: str | None,
    nomic_api_key: str | None,
) -> int | None:
    oai, tog, nom = _resolved_embedding_keys(
        openai_api_key=openai_api_key,
        together_api_key=together_api_key,
        nomic_api_key=nomic_api_key,
    )
    if oai:
        return OPENAI_VECTOR_DIM
    if tog:
        return together_vector_dim()
    if nom:
        return NOMIC_VECTOR_DIM
    return None


def _embed_openai(api_key: str, texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    out: list[list[float]] = []
    batch = 16
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        r = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=chunk)
        ordered = sorted(r.data, key=lambda x: x.index)
        for item in ordered:
            out.append(list(item.embedding))
    return out


def _embed_together(api_key: str, texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=TOGETHER_BASE_URL)
    model = _together_embed_model()
    out: list[list[float]] = []
    batch = 16
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        r = client.embeddings.create(model=model, input=chunk)
        ordered = sorted(r.data, key=lambda x: x.index)
        for item in ordered:
            out.append(list(item.embedding))
    return out


def _parse_nomic_body(data: dict) -> list[list[float]]:
    if "embeddings" in data:
        return [list(row) for row in data["embeddings"]]
    e = data.get("embedding")
    if e is not None and isinstance(e, (list, tuple)) and e:
        if isinstance(e[0], (int, float)):
            return [list(e)]
        return [list(row) for row in e]
    raise ValueError(f"Unexpected Nomic embedding response keys: {list(data.keys())}")


def _embed_nomic(
    api_key: str,
    texts: list[str],
    *,
    task_type: str,
) -> list[list[float]]:
    out: list[list[float]] = []
    # Nomic Atlas text API accepts small batches (official client uses max 10).
    batch = 10
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        r = safe_post_sync(
            NOMIC_EMBED_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": NOMIC_EMBED_MODEL,
                "texts": chunk,
                "task_type": task_type,
                "long_text_mode": "truncate",
            },
            timeout=120.0,
        )
        r.raise_for_status()
        out.extend(_parse_nomic_body(r.json()))
    return out


def _is_503ish_embed_error(exc: BaseException) -> bool:
    s = str(exc).lower()
    return "503" in str(exc) or "service_unavailable" in s


def _embed_texts_fallback_providers(
    texts: list[str],
    *,
    openai_api_key: str | None = None,
    together_api_key: str | None = None,
    nomic_api_key: str | None = None,
    nomic_task_type: str = "search_document",
) -> list[list[float]]:
    """Try each provider that has a key, in product priority order."""
    oai, tog, nom = _resolved_embedding_keys(
        openai_api_key=openai_api_key,
        together_api_key=together_api_key,
        nomic_api_key=nomic_api_key,
    )
    if oai:
        try:
            return _embed_openai(oai, texts)
        except Exception as e:
            logger.warning("embed_fallback_openai_failed: %s", e)
    if tog:
        try:
            return _embed_together(tog, texts)
        except Exception as e:
            logger.warning("embed_fallback_together_failed: %s", e)
    if nom:
        try:
            return _embed_nomic(nom, texts, task_type=nomic_task_type)
        except Exception as e:
            logger.warning("embed_fallback_nomic_failed: %s", e)
    raise ValueError("All embedding providers failed in fallback chain.")


def embed_texts(
    texts: list[str],
    *,
    openai_api_key: str | None = None,
    together_api_key: str | None = None,
    nomic_api_key: str | None = None,
    nomic_task_type: str = "search_document",
) -> list[list[float]]:
    oai, tog, nom = _resolved_embedding_keys(
        openai_api_key=openai_api_key,
        together_api_key=together_api_key,
        nomic_api_key=nomic_api_key,
    )
    logger.info(
        "embed_provider_check has_openai=%s has_together=%s has_nomic=%s",
        bool(oai),
        bool(tog),
        bool(nom),
    )
    if oai:
        return _embed_openai(oai, texts)
    if tog:
        return _embed_together(tog, texts)
    if nom:
        return _embed_nomic(nom, texts, task_type=nomic_task_type)
    raise ValueError(
        "Set OPENAI_API_KEY, TOGETHER_API_KEY, and/or NOMIC_API_KEY for embeddings. "
        "Groq is LLM-only, not used for embeddings."
    )


def embed_texts_with_retry(
    texts: list[str],
    *,
    openai_api_key: str | None = None,
    together_api_key: str | None = None,
    nomic_api_key: str | None = None,
    nomic_task_type: str = "search_document",
    max_retries: int = 3,
) -> list[list[float]]:
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return embed_texts(
                texts,
                openai_api_key=openai_api_key,
                together_api_key=together_api_key,
                nomic_api_key=nomic_api_key,
                nomic_task_type=nomic_task_type,
            )
        except Exception as e:
            last_err = e
            if _is_503ish_embed_error(e) and attempt < max_retries - 1:
                wait = 2**attempt
                logger.warning("embed_503_retry attempt=%s wait=%s err=%s", attempt, wait, e)
                time.sleep(wait)
                continue
            break
    try:
        return _embed_texts_fallback_providers(
            texts,
            openai_api_key=openai_api_key,
            together_api_key=together_api_key,
            nomic_api_key=nomic_api_key,
            nomic_task_type=nomic_task_type,
        )
    except Exception as fe:
        logger.error("embed_all_providers_failed primary=%s fallback=%s", last_err, fe)
        if last_err is not None:
            raise last_err from fe
        raise


def embed_query_text(
    text: str,
    *,
    openai_api_key: str | None = None,
    together_api_key: str | None = None,
    nomic_api_key: str | None = None,
) -> list[float] | None:
    try:
        vecs = embed_texts(
            [text[:8000]],
            openai_api_key=openai_api_key,
            together_api_key=together_api_key,
            nomic_api_key=nomic_api_key,
            nomic_task_type="search_query",
        )
        return vecs[0] if vecs else None
    except Exception:
        return None
