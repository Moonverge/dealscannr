# DealScannr ingestion CLI

`python -m ingestion "Company Name"` — fetch public text → chunk → embed → Qdrant `dealscannr_chunks`.

## Requirements

Same embedding env vars as the API (`OPENAI_API_KEY`, `TOGETHER_API_KEY`, `NOMIC_API_KEY`, etc.). Set `PYTHONPATH` to the parent of `ingestion` and `rag` (the `packages` directory).

## Vector dimension guard

Before upsert, the CLI calls **`ingestion.dim_guard.verify_collection_dim_sync`**. If the collection already exists with a **different** vector size than the active embedding provider, ingestion **aborts** with a clear error — drop the collection or switch provider.

The scan pipeline uses the same guard (async) before embedding when `QDRANT_URL` is set.

## Example

```bash
cd /path/to/repo
export PYTHONPATH=./packages
./packages/api/.venv/bin/python -m ingestion "Acme Corp"
```

Successful dim check prints: `✓ Collection dim matches: {dim}d (current embedding provider)`.
