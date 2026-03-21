import argparse
import re
import sys

from qdrant_client import QdrantClient

from rag.embeddings import embed_texts, embedding_vector_dim

from .chunk_text import build_chunk_payloads, split_blocks
from .config import settings
from .fetch_public import fetch_for_company
from .qdrant_store import upsert_chunks


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "unknown"


def title_case(name: str) -> str:
    import re as _re

    s = name.strip()
    if not s:
        return s
    parts = _re.split(r"(\s+|[\-&/])", s)
    out: list[str] = []
    for p in parts:
        if not p or _re.fullmatch(r"[\s\-&/]+", p):
            out.append(p)
        elif len(p) == 1:
            out.append(p.upper())
        else:
            out.append(p[0].upper() + p[1:].lower())
    return "".join(out)


def run(company_query: str) -> int:
    dim = embedding_vector_dim(
        settings.openai_api_key,
        settings.together_api_key,
        settings.nomic_api_key,
    )
    if dim is None:
        print(
            "Set OPENAI_API_KEY, TOGETHER_API_KEY, and/or NOMIC_API_KEY for embeddings (ingestion).",
            file=sys.stderr,
        )
        return 1
    name = company_query.strip()
    company_id = slug(name)
    display = title_case(name)
    raw, source_list = fetch_for_company(name, settings.firecrawl_api_key)
    if not raw:
        print("No text fetched; check FIRECRAWL_API_KEY or network.", file=sys.stderr)
        return 1
    blocks = split_blocks(raw)
    if not blocks:
        blocks = [("", raw)]
    texts, url_per_chunk = build_chunk_payloads(blocks)
    pairs = [(t, u) for t, u in zip(texts, url_per_chunk) if t.strip()]
    texts = [p[0] for p in pairs]
    url_per_chunk = [p[1] for p in pairs]
    if not texts:
        print("Nothing to embed.", file=sys.stderr)
        return 1
    try:
        vectors = embed_texts(
            texts,
            openai_api_key=settings.openai_api_key,
            together_api_key=settings.together_api_key,
            nomic_api_key=settings.nomic_api_key,
        )
    except Exception as e:
        print(f"Embedding failed: {e}", file=sys.stderr)
        return 1
    client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
    from ingestion.dim_guard import verify_collection_dim_sync
    from ingestion.qdrant_store import COLLECTION

    try:
        verify_collection_dim_sync(client, COLLECTION, dim)
        print(f"✓ Collection dim matches: {dim}d (current embedding provider)")
    except ValueError as e:
        print(f"✗ Dim mismatch — see above. Aborting.\n{e}", file=sys.stderr)
        return 1
    n = upsert_chunks(
        client,
        company_id=company_id,
        company_name=display,
        texts=texts,
        vectors=vectors,
        source_urls=url_per_chunk if url_per_chunk else source_list,
        source_type="web_ingest",
        vector_size=dim,
    )
    print(f"Upserted {n} vectors for {display} ({company_id}) into {settings.qdrant_url}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest public web snapshot into Qdrant")
    p.add_argument("company", help="Company name to ingest")
    args = p.parse_args()
    raise SystemExit(run(args.company))


if __name__ == "__main__":
    main()
