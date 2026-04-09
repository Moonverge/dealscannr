# DEALSCANNR — Master Prompt & AI Context

> **Use this as the single source of context when implementing, reviewing, or extending DEALSCANNR.** Read DEALSCANNR_PRODUCT.md and DEALSCANNR_ARCHITECTURE.md for full detail; this file is the compressed playbook.

---

## 1. Product in One Sentence

**DEALSCANNR** cuts investor due diligence from 2 weeks to ~60 seconds by returning an AI-generated intelligence report (team, legal, engineering, hiring, customer, founder, product signals + red/yellow/green verdict) from a single company name or natural-language query.

- **Users:** Angels, micro-VCs, solo GPs (wedge); later family offices, PE, corp VC.
- **MVP (v0):** One input (company name) → one output (intelligence report). No dashboard, no accounts.
- **Moat:** Cross-source “dirty” signal indexing (court, LinkedIn org, GitHub, job postings, podcasts, patents, app reviews, news, Crunchbase) with entity resolution and natural language interface.

---

## 2. Monorepo Layout

```
dealscannr/
├── packages/
│   ├── api/          # @dealscannr/api — FastAPI (port 5200)
│   ├── web/          # @dealscannr/web — React 19 + TS + Vite (port 5100)
│   ├── ingestion/    # @dealscannr/ingestion — scrapers + pipeline
│   └── rag/          # @dealscannr/rag — LlamaIndex RAG (query → report)
├── infra/            # qdrant, redis, mongo configs
├── e2e/              # E2E tests: API (pytest) + Web (Playwright)
├── docker-compose.yml
├── README.md
└── docs/
    ├── DEALSCANNR_PRODUCT.md
    ├── DEALSCANNR_ARCHITECTURE.md
    ├── DEALSCANNR_MASTER.md   # this file
    └── TRACKER_TODO.md
```

---

## 3. Tech Stack (Canonical)

| Layer        | Tech |
|-------------|------|
| Frontend    | React 19, TypeScript, Vite, Tailwind, Zustand, Axios, React Query |
| Backend API | FastAPI, Uvicorn, Motor (MongoDB), Redis, Pydantic v2, httpx |
| RAG        | LlamaIndex, Qdrant, **GROQ** (see below), OpenAI embeddings |
| Ingestion   | Python, Firecrawl, Playwright, Redis queues |
| Infra       | Docker Compose: MongoDB 5300, Redis 5400, Qdrant 5500/5501 |

---

## 4. LLM: GROQ (Not Claude)

- **All LLM calls use GROQ.** Do not use Claude/Anthropic in code or env.
- **Env:** `GROQ_API_KEY` (required for RAG synthesis and scoring).
- **Suggested models:**
  - **Synthesis (full report):** `llama-3.3-70b-versatile` or `llama3-70b-8192`.
  - **Scoring (red/yellow/green):** same or a smaller/faster model if available (e.g. `llama3-8b-8192`).
- **Integration:** LlamaIndex `llama-index-llms-groq`; instantiate with `Groq(model="...", api_key=os.getenv("GROQ_API_KEY"))`.
- **Prompts:** Reuse the same system/synthesis/scoring prompt design from DEALSCANNR_ARCHITECTURE.md; only the LLM backend is GROQ.

---

## 5. API Surface (Must Hold)

- `POST /api/search` — main query → triggers RAG → returns or streams report.
- `GET /api/reports/:id` — fetch saved report.
- `GET /api/companies/:slug` — company metadata + cached report status.
- `GET /health` — health check (for E2E and ops).

Base URL for frontend: `VITE_API_URL` (e.g. `http://localhost:5200`).

---

## 6. RAG Pipeline (Order Preserved)

1. **Query parsing** — entity + intent.
2. **Retrieval** — Qdrant hybrid (dense + sparse), top-k (e.g. 20).
3. **Rerank** — cross-encoder, top-8.
4. **Synthesis** — GROQ + structured prompt → `IntelligenceReport`.
5. **Scoring** — GROQ → verdict (green/yellow/red) + confidence.

Schema source of truth: `packages/rag/schema/` (report, signal, chunk). Frontend types must mirror these.

---

## 7. Environment Variables (Canonical List)

```bash
# API
DATABASE_URL=mongodb://localhost:5300/dealscannr
REDIS_URL=redis://localhost:5400
QDRANT_URL=http://localhost:5500
GROQ_API_KEY=                    # required for RAG (synthesis + scoring)
OPENAI_API_KEY=                  # embeddings only (e.g. text-embedding-3-small)
FIRECRAWL_API_KEY=

# Ingestion
GITHUB_TOKEN=
COURTLISTENER_API_KEY=
NEWSAPI_KEY=

# Web
VITE_API_URL=http://localhost:5200
```

---

## 8. Conventions & Rules

- **Ports:** 5100 (web), 5200 (api), 5300 (MongoDB), 5400 (Redis), 5500/5501 (Qdrant). Do not change without updating all references.
- **Qdrant collection:** `dealscannr_chunks` — do not rename without migration.
- **Chunking:** Per-source strategy (see DEALSCANNR_ARCHITECTURE.md); no single uniform chunk size.
- **Entity resolution:** Critical for quality; do not remove or oversimplify.
- **Ingestion ↔ API:** Communicate only via Redis queue and Qdrant; no direct process calls.
- **Freshness TTL:** Per source type (e.g. jobs 3d, GitHub 7d, court 30d); keep in scheduler.

---

## 9. E2E Strategy

- **API E2E:** `e2e/api/` — pytest, httpx (or FastAPI TestClient). Cover: `GET /health`, `POST /api/search` (minimal payload), optionally `GET /api/reports/:id` and `GET /api/companies/:slug`.
- **Web E2E:** `e2e/web/` — Playwright. Cover: load home, submit company search, (when implemented) view report page.
- **Run:** API tests against a running API (or in-docker); Web tests against a running dev build or served app. See `e2e/README.md` and `docs/TRACKER_TODO.md`.

---

## 10. AI / Developer Instructions

- Prefer **minimal, exact implementations** — no extra features or over-engineering.
- **Do not** run `npm run build`, `npm run start`, or `npm run dev` unless the user explicitly asks.
- Follow **frontend architecture** from user rules: `pages/`, `components/`, `hooks/`, `stores/`, `utils/api.routes.ts`, `utils/axios.instance.ts`, types in `types/`.
- Use **GROQ** and **GROQ_API_KEY** only for LLM; do not introduce Claude/Anthropic.
- When adding RAG prompts or schema, keep synthesis and scoring prompts in `packages/rag/prompts/` and schema in `packages/rag/schema/`.
- Before changing ports, collection names, or TTLs, update this master doc and `docs/TRACKER_TODO.md` if tasks are affected.

---

*Domain: dealscannr.com*
