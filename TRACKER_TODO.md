# DEALSCANNR — Tracker & Todo

> Single place to track phases, tasks, and status. Update as work completes.

**Legend:** `[ ]` Todo · `[-]` In progress · `[x]` Done · `[~]` Blocked / Deferred

---

## Phase 0 — Repo & Docs

| ID   | Task | Status |
|------|------|--------|
| 0.1  | Product doc (DEALSCANNR_PRODUCT.md) | [x] |
| 0.2  | Architecture doc (DEALSCANNR_ARCHITECTURE.md) | [x] |
| 0.3  | Master prompt / AI context (DEALSCANNR_MASTER.md) | [x] |
| 0.4  | Tracker (TRACKER_TODO.md) | [x] |
| 0.5  | E2E scaffold (e2e/ + API + Web) | [x] |
| 0.6  | .env.example with GROQ_API_KEY | [x] |

---

## Phase 1 — Infrastructure & API Skeleton

| ID   | Task | Status |
|------|------|--------|
| 1.1  | Root package.json workspaces (`packages/*`) | [ ] |
| 1.2  | docker-compose: mongodb, redis, qdrant | [ ] |
| 1.3  | packages/api: FastAPI app, /health | [ ] |
| 1.4  | packages/api: config (settings, database, redis) | [ ] |
| 1.5  | packages/api: middleware (rate_limit, error_handler, logging) | [ ] |
| 1.6  | API E2E: health check passing | [ ] |

---

## Phase 2 — RAG Engine

| ID   | Task | Status |
|------|------|--------|
| 2.1  | packages/rag: schema (report, signal, chunk, SourceType) | [ ] |
| 2.2  | packages/rag: prompts (system, synthesis, scoring) | [ ] |
| 2.3  | packages/rag: pipeline — query_parser | [ ] |
| 2.4  | packages/rag: pipeline — retriever (Qdrant hybrid) | [ ] |
| 2.5  | packages/rag: pipeline — reranker | [ ] |
| 2.6  | packages/rag: pipeline — synthesizer (GROQ) | [ ] |
| 2.7  | packages/rag: pipeline — scorer (GROQ) | [ ] |
| 2.8  | packages/rag: engine.py entry, LlamaIndex + GROQ | [ ] |
| 2.9  | Embedder (OpenAI text-embedding-3-small) | [ ] |

---

## Phase 3 — API Search & Reports

| ID   | Task | Status |
|------|------|--------|
| 3.1  | modules/search: router, controller, service | [ ] |
| 3.2  | POST /api/search → RAG engine → IntelligenceReport | [ ] |
| 3.3  | modules/reports: GET /api/reports/:id | [ ] |
| 3.4  | modules/companies: GET /api/companies/:slug | [ ] |
| 3.5  | API E2E: POST /api/search (minimal) | [ ] |
| 3.6  | API E2E: GET /api/reports/:id, GET /api/companies/:slug | [ ] |

---

## Phase 4 — Frontend (Web)

| ID   | Task | Status |
|------|------|--------|
| 4.1  | packages/web: Vite + React 19 + TS + Tailwind | [ ] |
| 4.2  | App, routes (/, /report/:slug) | [ ] |
| 4.3  | lib/api.ts (axios, VITE_API_URL) | [ ] |
| 4.4  | types/report.ts (mirror backend schema) | [ ] |
| 4.5  | pages/Home: search input + hero | [ ] |
| 4.6  | components/search: SearchBar, SearchSuggestions | [ ] |
| 4.7  | stores: searchStore, reportStore | [ ] |
| 4.8  | hooks: useSearch, useReport | [ ] |
| 4.9  | pages/Report: report view by slug | [ ] |
| 4.10 | components/report: ReportHeader, SignalCard, SignalGrid, VerdictBadge, SourceList | [ ] |
| 4.11 | Web E2E: load home, submit search | [ ] |
| 4.12 | Web E2E: open report page (when cached/mocked) | [ ] |

---

## Phase 5 — Ingestion (Background)

| ID   | Task | Status |
|------|------|--------|
| 5.1  | packages/ingestion: base scraper, queue (producer/worker) | [ ] |
| 5.2  | Scrapers: court, github, jobs, patents, app_store, news, podcast, wayback, crunchbase | [ ] |
| 5.3  | processing: cleaner, chunker (per-source), embedder, entity_resolver | [ ] |
| 5.4  | Upsert to Qdrant (dealscannr_chunks) | [ ] |
| 5.5  | scheduler: freshness TTL, re-ingest stale | [ ] |

---

## Phase 6 — Polish & Ship MVP

| ID   | Task | Status |
|------|------|--------|
| 6.1  | Rate limiting (Redis) in production | [ ] |
| 6.2  | Error messages and logging consistent | [ ] |
| 6.3  | E2E run in CI (e.g. GitHub Actions) | [ ] |
| 6.4  | README: dev setup, env, run e2e | [ ] |

---

## E2E Quick Reference

| Suite | Location | Command (intended) |
|-------|----------|--------------------|
| API   | e2e/api/ | `pytest e2e/api/` (API_URL env) |
| Web   | e2e/web/ | `npx playwright test` (baseURL env) |

---

*Last updated: 2025-03-21*
