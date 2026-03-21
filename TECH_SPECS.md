# DealScannr — Technical Specifications

Monorepo: npm workspaces under `packages/*`. AI-powered company scan → due-diligence-style report; optional vector RAG (Qdrant) plus live web context.

---

## Runtime & tooling

| Requirement | Version / note |
|-------------|----------------|
| Node.js | 20+ |
| Python | 3.11+ (venv required on macOS/Homebrew system Python — PEP 668) |
| Package manager | npm (workspaces) |
| API server | Uvicorn (`uvicorn main:app --reload --port 5200`) |
| `PYTHONPATH` | Repo `packages` (parent of `api` + `rag` + `ingestion`) |

---

## Services & ports

| Service | Port(s) | Role |
|---------|---------|------|
| Web (Vite dev) | 5100 | React SPA |
| API (FastAPI) | 5200 | HTTP API |
| MongoDB (Docker) | 5300 → 27017 | Optional persistence (`DATABASE_URL`) |
| Redis (Docker) | 5400 → 6379 | Optional cache/session (`REDIS_URL`) |
| Qdrant (Docker) | 5500 (REST), 5501 (gRPC) | Vector store; collection `dealscannr_chunks` |

---

## Frontend (`packages/web`)

| Layer | Choice |
|-------|--------|
| Framework | React 19 |
| Build | Vite 5 |
| Language | TypeScript 5 |
| Styling | Tailwind CSS 3, PostCSS, Autoprefixer |
| Routing | React Router DOM 7 |
| HTTP | Axios |
| Server state | TanStack React Query 5 |
| Client state | Zustand 5 |
| API base | `VITE_API_URL` (default `http://localhost:5200`) |

---

## Backend (`packages/api`)

| Layer | Choice |
|-------|--------|
| Framework | FastAPI |
| ASGI | Uvicorn [standard] |
| Validation / settings | Pydantic 2, pydantic-settings |
| MongoDB | Motor (async) |
| Redis | redis-py |
| HTTP client | httpx |
| Logging | structlog |
| LLM | Groq SDK (`groq`) |
| Vectors / embeddings client | qdrant-client, openai |

---

## RAG & ingestion

| Package | Role |
|---------|------|
| `packages/rag` | Retrieval + synthesis; live context (e.g. DuckDuckGo JSON; optional Firecrawl); Groq completion |
| `packages/ingestion` | CLI: web snapshot → chunk → embed → Qdrant upsert (same crawl/search surface as live RAG where applicable) |

**Embeddings (ingestion / index):** one provider at a time; do not mix vector dimensions in `dealscannr_chunks`. Priority when multiple keys exist: OpenAI (e.g. 1536-d) → Together (default BGE large, 1024-d) → Nomic (768-d) → Groq (if enabled). See README for model/dim env overrides.

**Indexed vs live:** Scan path can use Qdrant + live web context without prior ingest; ingestion fills Qdrant so `raw_chunks_count > 0` for a company slug.

---

## External integrations (env-driven)

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | LLM for RAG synthesis; optional embeddings if account supports |
| `OPENAI_API_KEY` | Embeddings (and related APIs as wired in code) |
| `TOGETHER_API_KEY` | Together OpenAI-compatible `/v1/embeddings` |
| `NOMIC_API_KEY` | Nomic Atlas embeddings |
| `QDRANT_URL` | Vector DB (optional for API retrieval) |
| `FIRECRAWL_API_KEY` | Richer crawl/search + markdown snippets (optional) |
| `DATABASE_URL`, `REDIS_URL` | MongoDB / Redis when using Docker stack |
| `VITE_API_URL` | Browser-visible API origin only — no server secrets |
| `GITHUB_TOKEN`, `COURTLISTENER_API_KEY`, `NEWSAPI_KEY` | Ingestion / extended sources (see `.env.example`) |

Env load: root `.env` and/or `packages/api/.env` (package wins if both set). Ingestion resolves multiple paths — see `CODEBASE_AUDIT.md` §4.2.

---

## Testing (`e2e/`)

- **API:** pytest  
- **Web:** Playwright  

---

## Repo layout (summary)

```
packages/api        — FastAPI app
packages/web        — React + Vite + Tailwind
packages/rag        — RAG pipeline
packages/ingestion  — CLI ingest → Qdrant
e2e/                — API + web E2E
scripts/            — run-api, ingest helpers
```

Further architecture: `DEALSCANNR_ARCHITECTURE.md`, `DEALSCANNR_MASTER.md`, `CODEBASE_AUDIT.md`.

---

## LLM prompts & anti-hallucination

**Canonical module:** `packages/rag/prompts/grounding_contract.py`

- **`DEALSCANNR_ANALYST_SYSTEM_PROMPT`** — default system message for analyst-style Groq calls (includes grounding contract + universal rules).
- **`UNIVERSAL_LLM_RULES`** — must be reflected in **every** LLM completion (synthesis, scoring, future extractors): no priors for company facts, no gap-filling, JSON-only when required, report conflicts, conservative when thin context.
- **`synthesis_grounding_user_block()`** — append to synthesis **user** prompts so grounding survives system prompt truncation.
- **`SCORING_GROUNDING_RULES`** — second-pass scoring: verdict only from provided summary + signals JSON.

**Cursor:** `.cursor/rules/dealscannr.mdc` repeats stack + prompt rules for agents.

Do not copy long contract strings into new files; import from `grounding_contract.py` only.

---

## Structured scan reports (`ReportOutput`)

- **Schema:** `packages/rag/schema/llm_report.py` (and re-export `packages/api/models/report.py`).
- **Chunk context:** `packages/rag/pipeline/chunk_context.py` — Qdrant payload `chunk_id` (Mongo `ObjectId` string) when ingested; otherwise deterministic `sha256` 16-hex id.
- **Parse + validate + citation strip:** `packages/rag/pipeline/llm_report_output.py` — invalid JSON / Pydantic → `verdict=INSUFFICIENT`; hallucinated `chunk_id`s stripped and confidence −0.1 each (floor 0).
- **API:** `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/scans`, `GET /api/scans/{scan_id}/report` (202 processing, failed/missing → `INSUFFICIENT` body).

---

## Phase 3 — Connectors & scan pipeline

- **Connectors:** `packages/rag/connectors/` — `base.py`, `sec_edgar.py`, `courtlistener.py`, `github_connector.py`, `hiring_connector.py`, `news_connector.py`. All implement async `fetch()` with internal `asyncio.wait_for` timeout; exceptions → `empty_result`, never raise.
- **Runner:** `packages/rag/pipeline/runner.py` — `build_connectors`, `lane_coverage_from_results`, parallel `gather` (defensive against stray exceptions).
- **Scan pipeline:** `packages/api/modules/scans/pipeline.py` — per-connector Mongo `connector_runs` updates (`queued` → `running` → final), chunk `ObjectId`, `embed_texts`, Qdrant upsert (`scan_id`, `entity_id`, `chunk_id`, …), Mongo `chunks` collection, then `RAGEngine.run` with `scan_id` retrieval filter.
- **Retriever:** `retrieve_chunks(..., scan_id=...)` filters Qdrant payload `scan_id`; engine uses up to 40 chunks for real scans.
- **Status:** `GET /api/scans/{scan_id}/status` — lane rollup + `total_chunks` + `elapsed_seconds`.
- **Entity v2:** `POST /api/entity/resolve`, `POST /api/entity/confirm` + `rapidfuzz` (`packages/api/modules/entity/`).
- **Env (connectors):** `COURTLISTENER_API_KEY`, `GITHUB_TOKEN`, `NEWSAPI_KEY` (plus existing `FIRECRAWL_API_KEY`, embedding keys).
