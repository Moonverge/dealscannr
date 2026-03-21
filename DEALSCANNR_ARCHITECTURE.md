# DEALSCANNR — Monorepo Architecture & RAG System Design

> Reference document for AI-assisted development. Read this before touching any file.

---

## Monorepo Structure

```
dealscannr/
├── package.json                    # Root: workspaces ["packages/*"]
├── packages/
│   ├── api/                        # @dealscannr/api — FastAPI backend (Python)
│   ├── web/                        # @dealscannr/web — React frontend
│   ├── ingestion/                  # @dealscannr/ingestion — data scrapers + pipeline
│   └── rag/                        # @dealscannr/rag — RAG engine (LlamaIndex)
├── infra/
│   ├── qdrant/                     # Qdrant vector DB config
│   ├── redis/                      # Redis config
│   └── mongo/                      # MongoDB init
├── docker-compose.yml
├── docker-compose.prod.yml
└── docs/
```

---

## System Architecture Overview

```
User Query (company name or natural language)
        ↓
[ React Frontend ] — port 5100
        ↓ HTTP/WebSocket
[ FastAPI Backend ] — port 5200
        ↓
[ RAG Engine (LlamaIndex) ]
        ├── Query Understanding → intent + entity extraction
        ├── Vector Search → Qdrant (semantic similarity)
        ├── Reranking → cross-encoder rerank top-k results
        └── Response Synthesis → GROQ (llama-3.3-70b-versatile or llama3-70b-8192)
        ↓
[ Intelligence Report ]
        ↓
[ Frontend renders structured report ]

Background (async):
[ Ingestion Pipeline ]
        ├── Scrapers (Python + Firecrawl)
        ├── Data Cleaning + Chunking
        ├── Embedding (OpenAI or local)
        └── Upsert to Qdrant
```

---

## Package: `@dealscannr/api` (FastAPI Backend)

**Stack:** Python 3.11+, FastAPI, Uvicorn, Motor (async MongoDB), Redis, Pydantic v2, httpx

**Port:** 5200

**Layout:**

```
packages/api/
├── main.py                         # FastAPI app entry, mounts routers
├── config/
│   ├── settings.py                 # Pydantic BaseSettings, env vars
│   ├── database.py                 # Motor async MongoDB client
│   └── redis.py                    # Redis client (aioredis)
├── modules/
│   ├── search/
│   │   ├── router.py               # POST /search — main query endpoint
│   │   ├── controller.py           # Request handling, response shaping
│   │   └── service.py              # Calls RAG engine, assembles report
│   ├── reports/
│   │   ├── router.py               # GET /reports/:id — fetch saved reports
│   │   ├── controller.py
│   │   └── service.py
│   ├── companies/
│   │   ├── router.py               # GET /companies/:slug — company metadata
│   │   ├── controller.py
│   │   └── service.py
│   └── auth/                       # JWT auth (Phase 2+)
├── middleware/
│   ├── rate_limit.py               # Redis-backed rate limiting
│   ├── error_handler.py
│   └── logging.py                  # Structured JSON logs (structlog)
└── tests/
    └── test_search.py
```

**Key endpoints:**

```
POST /api/search          — main query, triggers RAG pipeline
GET  /api/reports/:id     — fetch a saved report
GET  /api/companies/:slug — company metadata + cached report status
GET  /health              — health check
GET  /docs                — Swagger UI (dev only)
```

---

## Package: `@dealscannr/rag` (RAG Engine)

This is the core intelligence layer. Everything else serves this.

**Stack:** Python, LlamaIndex, Qdrant client, GROQ API (llama-index-llms-groq), OpenAI embeddings

**Layout:**

```
packages/rag/
├── engine.py                       # Main RAGEngine class — entry point
├── pipeline/
│   ├── query_parser.py             # Extract entity name, query intent
│   ├── retriever.py                # Qdrant hybrid search (dense + sparse)
│   ├── reranker.py                 # Cross-encoder reranking (top-k)
│   ├── synthesizer.py              # GROQ API call, prompt assembly
│   └── scorer.py                   # Signal scoring (green/yellow/red)
├── prompts/
│   ├── system.py                   # System prompt for LLM (GROQ)
│   ├── synthesis.py                # Report synthesis prompt
│   └── scoring.py                  # Red/yellow/green flag scoring prompt
├── schema/
│   ├── report.py                   # Pydantic: IntelligenceReport
│   ├── signal.py                   # Pydantic: Signal, SignalCategory
│   └── chunk.py                    # Pydantic: DocumentChunk (what goes into Qdrant)
└── utils/
    ├── embedder.py                 # Embedding wrapper (OpenAI text-embedding-3-small)
    └── chunker.py                  # Smart chunking strategy per source type
```

### RAG Pipeline (step by step)

```
1. QUERY PARSING
   Input: "Tell me about Acme Corp"
   Output: { entity: "Acme Corp", intent: "full_due_diligence" }

2. RETRIEVAL
   - Dense search: cosine similarity on entity + query embedding
   - Sparse search: BM25 keyword match (for proper nouns, legal terms)
   - Hybrid fusion: RRF (Reciprocal Rank Fusion) of both results
   - Top-k: 20 chunks returned

3. RERANKING
   - Cross-encoder model rescores top-20 chunks
   - Returns top-8 most relevant

4. SYNTHESIS
   - Top-8 chunks assembled as context
   - Sent to GROQ with structured output prompt
   - Returns: IntelligenceReport (see schema below)

5. SCORING
   - Separate GROQ call for red/yellow/green verdict
   - Based on signal weights per category
```

### IntelligenceReport Schema

```python
class IntelligenceReport(BaseModel):
    company_name: str
    generated_at: datetime
    verdict: Literal["green", "yellow", "red"]
    confidence: float                           # 0.0 - 1.0
    summary: str                                # 2-3 sentence plain English summary
    signals: list[Signal]
    sources_used: list[str]
    raw_chunks_count: int

class Signal(BaseModel):
    category: SignalCategory
    title: str
    description: str
    sentiment: Literal["positive", "negative", "neutral"]
    source: str
    date_detected: Optional[datetime]
    weight: float                               # how much this affects verdict

class SignalCategory(str, Enum):
    TEAM = "team"
    LEGAL = "legal"
    ENGINEERING = "engineering"
    HIRING = "hiring"
    CUSTOMER = "customer"
    FINANCIALS = "financials"
    FOUNDER = "founder"
    PRODUCT = "product"
```

### Qdrant Document Chunk Schema

```python
class DocumentChunk(BaseModel):
    id: str                                     # UUID
    company_id: str                             # normalized company slug
    company_name: str
    source_type: SourceType                     # court | github | linkedin | etc
    source_url: str
    raw_text: str
    embedding: list[float]                      # 1536-dim (text-embedding-3-small)
    metadata: dict                              # flexible, source-specific
    ingested_at: datetime
    freshness_score: float                      # decays over time, triggers re-scrape

class SourceType(str, Enum):
    COURT_FILING = "court_filing"
    GITHUB = "github"
    JOB_POSTING = "job_posting"
    LINKEDIN_ORG = "linkedin_org"
    PODCAST_TRANSCRIPT = "podcast_transcript"
    PATENT = "patent"
    APP_STORE = "app_store"
    NEWS = "news"
    WAYBACK = "wayback"
    CRUNCHBASE = "crunchbase"
```

---

## Package: `@dealscannr/ingestion` (Data Pipeline)

**Stack:** Python, Firecrawl, Playwright (for JS-heavy sites), APScheduler, BullMQ-style via Redis queues

**Layout:**

```
packages/ingestion/
├── orchestrator.py                 # Kick off ingestion for a company
├── scrapers/
│   ├── base.py                     # BaseScraper abstract class
│   ├── court.py                    # PACER / CourtListener
│   ├── github.py                   # GitHub API (commit velocity, stars, forks)
│   ├── jobs.py                     # LinkedIn Jobs + Indeed via Firecrawl
│   ├── patents.py                  # USPTO / Google Patents
│   ├── app_store.py                # App Store + Play Store ratings/reviews
│   ├── news.py                     # NewsAPI + Firecrawl
│   ├── podcast.py                  # Whisper transcription on podcast episodes
│   ├── wayback.py                  # Wayback Machine CDX API
│   └── crunchbase.py               # Crunchbase public API
├── processing/
│   ├── cleaner.py                  # Strip HTML, normalize whitespace
│   ├── chunker.py                  # Source-aware chunking strategy
│   ├── embedder.py                 # Batch embedding calls
│   └── entity_resolver.py         # Link "John Santos @ Acme" across sources
├── queue/
│   ├── producer.py                 # Push ingestion jobs to Redis queue
│   └── worker.py                   # Process jobs, upsert to Qdrant
└── scheduler.py                    # APScheduler: re-ingest stale companies
```

### Chunking Strategy Per Source

Different sources need different chunking. Do NOT apply uniform chunking.

| Source | Chunk Strategy |
|---|---|
| Court filing | By paragraph, max 512 tokens, preserve case name + date in metadata |
| GitHub | By commit message batch (7-day windows), include repo + author |
| Job posting | Full posting as one chunk (usually <300 tokens) |
| Podcast transcript | By speaker turn, max 400 tokens |
| News article | By paragraph, first 3 paragraphs weighted higher |
| Patent | Claims section only (most signal-dense) |
| App review | Individual review as chunk, include rating + date |

### Entity Resolution

Critical for report quality. Same person/company appears differently across sources.

```python
# These must resolve to the same entity:
"Acme Corp" == "Acme Corporation" == "Acme Inc."
"John Santos, CTO at Acme" == "J. Santos (Acme)" == "@jdsantos on GitHub"
```

Strategy:
1. Fuzzy string matching (RapidFuzz) for company names
2. LinkedIn URL as canonical person ID where available
3. Domain-based company resolution as fallback
4. Manual override table in MongoDB for known edge cases

### Freshness + Re-ingestion

Every `DocumentChunk` has a `freshness_score` that decays based on source volatility:

| Source | TTL before re-scrape |
|---|---|
| Job postings | 3 days (changes fast) |
| GitHub | 7 days |
| News | 1 day |
| Court filings | 30 days (slow-moving) |
| Patents | 90 days |
| App store | 7 days |

APScheduler checks daily, queues stale companies for re-ingestion.

---

## Package: `@dealscannr/web` (React Frontend)

**Stack:** React 19, TypeScript, Vite, Tailwind CSS, Zustand, Axios, React Query

**Port:** 5100

**Layout:**

```
packages/web/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   └── routes.tsx
│   ├── pages/
│   │   ├── Home.tsx                # Search input, hero
│   │   ├── Report.tsx              # Full intelligence report view
│   │   ├── Dashboard.tsx           # Saved reports, history (Phase 2)
│   │   └── Auth.tsx                # Login/signup (Phase 2)
│   ├── components/
│   │   ├── search/
│   │   │   ├── SearchBar.tsx
│   │   │   └── SearchSuggestions.tsx
│   │   ├── report/
│   │   │   ├── ReportHeader.tsx    # Company name, verdict badge, confidence
│   │   │   ├── SignalCard.tsx      # Individual signal display
│   │   │   ├── SignalGrid.tsx      # All signals grouped by category
│   │   │   ├── VerdictBadge.tsx    # Green/Yellow/Red
│   │   │   └── SourceList.tsx      # Sources used in report
│   │   └── ui/
│   │       ├── Spinner.tsx
│   │       ├── Badge.tsx
│   │       └── Tooltip.tsx
│   ├── stores/
│   │   ├── searchStore.ts          # Current query, loading state
│   │   └── reportStore.ts          # Current report, history
│   ├── hooks/
│   │   ├── useSearch.ts            # Trigger search, poll for result
│   │   └── useReport.ts            # Fetch + cache report
│   ├── lib/
│   │   ├── api.ts                  # Axios instance, base URL config
│   │   └── utils.ts
│   └── types/
│       └── report.ts               # Mirror of backend IntelligenceReport schema
```

### Report Page Flow

```
User lands on /report/:company_slug
        ↓
useReport hook → GET /api/reports/:slug
        ↓
If cached (< TTL): render immediately
If not cached: show skeleton → POST /api/search → poll status → render
        ↓
ReportHeader: company name + verdict badge
SignalGrid: signals grouped by category (team, legal, engineering...)
SourceList: transparency layer — show what we scanned
```

---

## Infrastructure (Docker Compose)

| Service | Role | Port |
|---|---|---|
| web | React frontend (Vite dev server) | 5100 |
| api | FastAPI backend | 5200 |
| mongodb | Primary DB | 5300 |
| redis | Cache + job queue | 5400 |
| qdrant | Vector DB | 5500 (HTTP), 5501 (gRPC) |
| ingestion-worker | Background scraping + embedding | — |

```yaml
# docker-compose.yml (abbreviated)
services:
  web:
    build: ./packages/web
    ports: ["5100:5100"]

  api:
    build: ./packages/api
    ports: ["5200:5200"]
    depends_on: [mongodb, redis, qdrant]

  mongodb:
    image: mongo:7
    ports: ["5300:27017"]

  redis:
    image: redis:7-alpine
    ports: ["5400:6379"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["5500:6333", "5501:6334"]
    volumes: ["qdrant_storage:/qdrant/storage"]

  ingestion-worker:
    build: ./packages/ingestion
    depends_on: [redis, qdrant, mongodb]
```

---

## Environment Variables

```bash
# API
DATABASE_URL=mongodb://localhost:5300/dealscannr
REDIS_URL=redis://localhost:5400
QDRANT_URL=http://localhost:5500
GROQ_API_KEY=
OPENAI_API_KEY=                     # for embeddings only
FIRECRAWL_API_KEY=

# Ingestion
GITHUB_TOKEN=
COURTLISTENER_API_KEY=
NEWSAPI_KEY=

# Web
VITE_API_URL=http://localhost:5200
```

---

## Key Architectural Decisions

### Why Qdrant over Pinecone/Weaviate
- Self-hostable — zero cost in dev, full control in prod
- Supports hybrid search (dense + sparse) natively
- Rust-based, extremely fast
- No vendor lock-in

### Why LlamaIndex over LangChain
- Better RAG primitives out of the box
- Cleaner retrieval pipeline abstraction
- Less boilerplate for the ingestion → index → query flow

### Why GROQ for synthesis
- Fast inference, cost-effective
- Use `llama-3.3-70b-versatile` or `llama3-70b-8192` for synthesis
- Use smaller model (e.g. `llama3-8b-8192`) for scoring pass if desired
- Set `GROQ_API_KEY` in env

### Why FastAPI over Express
- Python-native — same language as RAG and ingestion layers
- Async first — matches Motor (MongoDB) and httpx
- Pydantic validation built in — schema consistency across layers
- Auto-generated OpenAPI docs

### Embedding Model Choice
- `text-embedding-3-small` (OpenAI) — 1536 dims, $0.02/1M tokens
- Cheap enough for ingestion at scale
- Consistent quality across source types
- Swap to local model (e5-large) if cost becomes issue at scale

---

## Development Setup

```bash
# Prerequisites: Python 3.11+, Node 20+, Docker

# Start infrastructure
docker compose up mongodb redis qdrant -d

# Start API (use a venv — macOS/Homebrew blocks system pip; see README)
# From repo root:
npm run api
# Or manually:
cd packages/api && python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
export PYTHONPATH="$(cd ../.. && pwd)/packages"
uvicorn main:app --reload --port 5200

# Start Web
cd packages/web
npm install
npm run dev

# Start ingestion worker
cd packages/ingestion
pip install -r requirements.txt
python worker.py
```

---

## Notes for AI Developers

- **Do not change port assignments without updating all references** — ports are fixed in docker-compose.yml
- **All schemas are source of truth in `packages/rag/schema/`** — frontend types must mirror these exactly
- **Chunking strategy is per-source** — see ingestion/processing/chunker.py comments, do not apply uniform chunking
- **Entity resolution is the hardest problem** — do not simplify it, the quality of reports depends on it
- **GROQ model routing:** synthesis = llama-3.3-70b-versatile (or llama3-70b-8192), scoring = same or llama3-8b-8192; use GROQ_API_KEY
- **Qdrant collection name:** `dealscannr_chunks` — do not rename without migration
- **Freshness TTL is per source type** — see ingestion/scheduler.py, do not make it uniform
- **The ingestion worker and the API are separate processes** — they communicate only via Redis queue and Qdrant, never direct function calls
