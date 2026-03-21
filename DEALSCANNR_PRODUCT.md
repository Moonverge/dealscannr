# DEALSCANNR — Product Overview

> AI-powered due diligence for investors who move fast.

---

## What Is It

DEALSCANNR is a private market intelligence platform. An investor types a company name and gets a full intelligence report in seconds — synthesized from sources that no existing tool cross-references properly.

It replaces 2 weeks of manual research with a 60-second AI scan.

**One-liner for investors:**
> "We cut due diligence from 2 weeks to 60 seconds."

---

## The Problem

When an investor hears about a startup, they need to answer one question fast:

> *Is this worth my time and money?*

Right now they manually:
- Google the company and founders
- Check LinkedIn for team changes
- Search court records for litigation
- Check GitHub for engineering activity
- Look up job postings for growth signals
- Listen to podcasts where founders say things off the record
- Read Crunchbase and PitchBook for funding history

This takes **days**. Angels and micro-VCs look at 100+ deals a year. They physically cannot do this for every deal. So they either skip research (risky) or miss deals (costly).

**DEALSCANNR solves this.**

---

## The Solution

User flow:

```
Investor hears about a startup
→ Goes to DEALSCANNR
→ Types company name
→ Gets full intelligence report:
   ├── Team signals (who joined, who left, exec changes)
   ├── Legal signals (active litigation, filings)
   ├── Engineering signals (GitHub commit velocity, repo activity)
   ├── Hiring signals (job postings = growth or pivot proxy)
   ├── Customer sentiment (app store reviews, G2, Trustpilot)
   ├── Founder track record (past companies, podcast mentions)
   ├── Patent filings (R&D activity signal)
   └── Red flags + green flags summary (AI-generated verdict)
→ Investor decides: worth a meeting or pass
```

DEALSCANNR is not replacing investor judgment. It is replacing the **grunt research work** before judgment happens.

---

## Target Users

**Primary (wedge):**
- Angel investors (5,000+ active syndicates on AngelList alone)
- Micro-VCs (sub-$50M funds, lean teams, no research analysts)
- Solo GPs

**Secondary (expansion):**
- Family offices doing deal screening
- PE associates doing pre-LOI research
- Corporate VC teams

**Why angels first:**
- Low CAC — tight community, high word of mouth
- High volume of deals — most pain felt here
- Can't afford PitchBook — perfect price sensitivity fit

---

## Data Sources (The Real Moat)

This is what separates DEALSCANNR from every competitor. We don't just index clean, structured data. We index **dirty signals** nobody else is collecting properly.

| Source | Signal |
|---|---|
| Court records | Litigation = company stress |
| LinkedIn org changes | Executive departures = red flag |
| Job postings | Hiring velocity = growth proxy |
| GitHub commit history | Engineering health |
| Podcast transcripts | Founders say things here they don't publish |
| Patent filings | R&D activity and future product direction |
| App store reviews + rankings | Customer satisfaction trend |
| Wayback Machine snapshots | Product pivots over time |
| News and press mentions | Sentiment and traction |
| Crunchbase/PitchBook (public layer) | Baseline funding data |

---

## Competitors

| Competitor | What They Do | Why They Fall Short |
|---|---|---|
| **PitchBook** | Largest private company database | $30K/year, no AI, no natural language, you browse manually |
| **Crunchbase** | Startup funding data | Surface level only, no signal synthesis, often outdated |
| **CB Insights** | Market research + company data | Bloated, expensive, slow, not queryable in plain English |
| **Harmonic.ai** | Job posting signals | One data source only, no cross-referencing |
| **Dealroom** | EU-focused private market data | Weak on US private signals, no AI layer |
| **Visible.vc** | Founder-facing portfolio tool | Founder-side only, not investor research |
| **Perplexity** | General web AI search | Not specialized, no private market focus, no signal scoring |

**Nobody** is doing cross-source private signal RAG with a consumer-grade UX at an accessible price point.

---

## Our Edge

### 1. Cross-source signal synthesis
Competitors give you a database to browse. DEALSCANNR gives you an analyst who already read everything.

### 2. Dirty signal indexing
We ingest sources nobody is structuring properly — court filings, podcast transcripts, org chart changes, commit velocity. This is not in PitchBook.

### 3. Entity resolution
Linking "John Santos @ Acme Inc" across 12 different data sources is technically hard. Most competitors do it poorly. Good entity resolution = better reports.

### 4. Natural language interface
Type a question like a human. Get an answer like a human. No learning curve, no filters to configure.

### 5. Price accessibility
PitchBook is $30K/year. DEALSCANNR starts at $500/month. Same angel who can't afford PitchBook can afford us.

### 6. Speed
60 seconds vs 2 weeks. This is the pitch.

---

## Revenue Model

| Tier | Price | Target |
|---|---|---|
| Starter | $99/mo | Individual angels, first-time investors |
| Pro | $500/mo | Active angels, AngelList syndicates |
| Team | $2,500/mo | Micro-VCs, family offices |
| Enterprise | $15,000/mo | PE firms, large VC funds |

**Wedge pricing strategy:** Start cheap enough that angels adopt without approval. Let word-of-mouth pull in the higher tiers.

---

## Go-To-Market (Solo Dev Playbook)

### Phase 1 — Infiltrate, don't advertise
- Give free access to 10 active angel investors
- Ask for feedback, not testimonials
- Let them talk

### Phase 2 — Build in public
- Post AI-generated report outputs on X and LinkedIn
- Not "I built a tool" — post the **output**
- Example post: *"Asked DEALSCANNR about [company] — here's what it found that PitchBook missed"*

### Phase 3 — Own one community
- Pick one: VC Twitter, Indie Hackers, or AngelList community
- Do not spread thin
- Become the go-to person for AI due diligence in that room

### Phase 4 — Cold email PE associates
- Not partners — **associates**
- They do grunt DD work
- They are the internal champions

### The headline post:
> *"I built PitchBook in 30 days"*
> Post on X + LinkedIn + Indie Hackers simultaneously.
> That headline alone gets 50K+ impressions in the startup space.

---

## MVP Scope (v0)

Dead simple. Prove value before adding complexity.

**One input. One output.**

```
[ Company name input ]
        ↓
[ Intelligence Report ]
  - Team signals
  - Legal signals
  - Engineering signals
  - Hiring signals
  - AI verdict: Green / Yellow / Red
```

No dashboard. No filters. No user accounts even for v0.
Just one thing done extremely well.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Ingestion | Python scrapers + Firecrawl |
| Vector DB | Qdrant (self-hostable, cost-efficient) |
| RAG Engine | LlamaIndex + GROQ |
| Backend | FastAPI |
| Frontend | React + TypeScript + Tailwind |
| Queue | BullMQ + Redis |
| Storage | Cloudflare R2 |

---

## Investor Pitch (30 seconds)

> "DEALSCANNR is AI due diligence for investors who move fast. We cut company research from 2 weeks to 60 seconds by scanning sources that PitchBook doesn't even collect — court filings, engineering activity, founder podcast mentions, org chart changes. We're targeting the 50,000+ active angels and micro-VCs who look at 100 deals a year and can't afford $30K for PitchBook. We start at $99 a month."

---

*Domain: dealscannr.com*
