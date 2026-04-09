# DealScannr

**Pre-call intelligence for angels and micro-VCs.**

Surface litigation risk, engineering health, and hiring signals for any company — in about a minute, with citations.

> The scan you run after Crunchbase, before the first call.

## What it does

An investor types a company name. DealScannr scans:

- **SEC EDGAR** — filings, enforcement actions, regulatory activity
- **CourtListener** — federal court records and active litigation
- **GitHub** — public engineering activity, org health, commit trends
- **Job boards** — hiring velocity, role mix, growth signals
- **News & Wikipedia** — recent coverage, founder context, company background

It returns a structured report with:

- **Verdict** — MEET / PASS / FLAG / INSUFFICIENT
- **Risk triage** — clean / watch / flag / unknown
- **Executive brief** — short analyst summary with inline citations
- **Before the call, probe** — three specific questions grounded in evidence
- **Cited sections** — claims tied to retrieved source chunks

## Why it exists

Crunchbase tells you who a company is.  
DealScannr tells you what could embarrass you in the meeting.

Angels and micro-VCs screening 20–50 deals a week have no purpose-built pre-call research tool. Enterprise data rooms are priced for institutions. General-purpose AI search optimizes for answers, not entity-safe citations or diligence-style structure. Manual search burns time and still surfaces marketing pages first.

DealScannr is built for that gap: fast, structured, citation-grounded pre-call scans. **Pro from $99/month** — see the app for current plans.

## Sample report

**Atlassian** · atlassian.com · PASS · Risk: watch

Executive summary cites Wikipedia and filings; probe questions point to litigation, market moves, and strategy — each tied to evidence chunks in the full UI.

## Architecture

```
packages/
  api/          FastAPI — auth, scans, billing, reports, entities
  web/          React + Vite frontend
  rag/          Connectors, embeddings, RAG engine, synthesis, grounding
  ingestion/    CLI ingest into Qdrant
e2e/            pytest (API) + Playwright (web)
scripts/        Dev helpers
```

**Stack**

- Backend: FastAPI, Python 3.11+, Motor (async MongoDB)
- Frontend: React 19, Vite 5, TypeScript, Tailwind CSS
- AI: OpenAI (embeddings + synthesis; optional Groq fallback)
- Vector DB: Qdrant
- Database: MongoDB
- Cache: Redis
- Auth: JWT
- Billing: Stripe

**Further documentation:** product, architecture, audit playbook, tech specs, and tracker live under [`docs/`](docs/) (start with [`docs/DEALSCANNR_MASTER.md`](docs/DEALSCANNR_MASTER.md)).

**Connectors (high level)**

- SEC EDGAR, CourtListener, GitHub, hiring (e.g. Remotive / Adzuna), news (e.g. GDELT / RSS / DuckDuckGo), Wikipedia, Clearbit autocomplete (via API proxy for entity UX).

## Anti-hallucination design

Factual claims in synthesis are tied to retrieved chunks: stable chunk IDs, required inline citations, post-validation that strips unknown IDs and adjusts confidence, and thin-evidence rules that cap or force INSUFFICIENT when appropriate.

## Quick start

```bash
git clone https://github.com/aeolus87/dealscannr.git
cd dealscannr

cp .env.example .env
# Set at least OPENAI_API_KEY; see table below for the rest.

docker compose up -d
# MongoDB :5300, Redis :5400, Qdrant :5500 (REST) / :5501 (gRPC)

cd packages/api
python3 -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PYTHONPATH="$(cd .. && pwd)"   # parent of api/ + rag/ on path
uvicorn main:app --reload --port 5200

cd ../web
npm install && npm run dev
# http://localhost:5100 — set VITE_API_URL if the API is not on :5200
```

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes (for real scans) | Embeddings + synthesis |
| `GROQ_API_KEY` | No | LLM fallback |
| `QDRANT_URL` | For indexed RAG | Vector store |
| `DATABASE_URL` | Yes | MongoDB |
| `REDIS_URL` | Yes | Cache + rate limits |
| `JWT_SECRET` | Yes | Auth signing |
| `STRIPE_SECRET_KEY` | No | Billing |
| `COURTLISTENER_API_KEY` | No | Court data |
| `GITHUB_TOKEN` | No | Higher GitHub rate limits |
| `NEWSAPI_KEY` | No | NewsAPI |
| `FIRECRAWL_API_KEY` | No | Richer web fetch |

Load order: repo `.env` then `packages/api/.env` (package wins). Never put secrets in `VITE_*`.

## Running tests

```bash
# API (MongoDB reachable per DATABASE_URL)
cd e2e
pip install -r requirements.txt
PYTHONPATH=../packages:../packages/api pytest api/ -q

# Web typecheck
cd packages/web && npx tsc --noEmit

# Browser E2E (app running)
cd e2e/web && npx playwright test
```

## Roadmap

- [ ] Clearbit-style enrichment (employees, funding, tech stack) beyond autocomplete
- [ ] Deeper SEC narrative extraction beyond targeted items
- [ ] Hybrid retrieval (sparse + dense) for legal text
- [ ] Stronger diff / change summaries across rescans
- [ ] Browser extension workflows
- [ ] CRM webhooks (Notion, Airtable, …)

## License

MIT

---

*Not investment advice. Verify all material claims from primary sources before any investment decision.*
