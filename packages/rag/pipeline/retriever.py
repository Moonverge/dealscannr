import logging
from typing import Any

# Optional Qdrant; if not installed or no QDRANT_URL, we skip real retrieval
try:
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    from rag.utils.qdrant_client_factory import qdrant_client as _make_qdrant_client

    QDRANT_AVAILABLE = True
except Exception:
    QDRANT_AVAILABLE = False
    _make_qdrant_client = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


def retrieve_chunks(
    qdrant_url: str | None,
    collection: str,
    query_embedding: list[float] | None,
    company_slug: str | None,
    limit: int = 20,
    *,
    vector_size: int = 1536,
    scan_id: str | None = None,
    entity_id: str | None = None,
    qdrant_api_key: str | None = None,
) -> list[dict[str, Any]]:
    if not QDRANT_AVAILABLE or not qdrant_url or _make_qdrant_client is None:
        return []
    try:
        client = _make_qdrant_client(qdrant_url, qdrant_api_key)
        z = [0.0] * vector_size
        must: list = []
        if scan_id is not None and str(scan_id).strip() != "":
            must.append(FieldCondition(key="scan_id", match=MatchValue(value=str(scan_id))))
        if entity_id is not None and str(entity_id).strip() != "":
            must.append(FieldCondition(key="entity_id", match=MatchValue(value=str(entity_id))))
        if company_slug:
            must.append(FieldCondition(key="company_id", match=MatchValue(value=company_slug)))
        flt = Filter(must=must) if must else None
        kwargs: dict[str, Any] = {
            "collection_name": collection,
            "query": query_embedding or z,
            "limit": limit,
        }
        if flt is not None:
            kwargs["query_filter"] = flt
        response = client.query_points(**kwargs)
        results = response.points
        return [r.model_dump() if hasattr(r, "model_dump") else dict(r) for r in results]
    except Exception as e:
        logger.warning("qdrant_retrieve_failed collection=%s err=%s", collection, e)
        return []
