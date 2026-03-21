# DEALSCANNR — Production Vision, Competitor Bar & Differentiation

> **Purpose:** Define what “production-grade at competitor level” means for private-market intelligence, what is **missing** today relative to that bar, and what DealScannr can **add** that incumbents are structurally weak at.  
> **Companion docs:** [DEALSCANNR_PRODUCT.md](./DEALSCANNR_PRODUCT.md) (positioning), [DEALSCANNR_ARCHITECTURE.md](./DEALSCANNR_ARCHITECTURE.md) (system shape), [TRACKER_TODO.md](./TRACKER_TODO.md) (execution backlog).

---

## 1. Executive summary

**Competitors at production** sell **trust**: licensed or crawled **structured** data, known coverage, legal/commercial posture, SLAs, sales/support, and workflows tuned for institutions.

**DealScannr’s full vision** is not “another database UI” but **cross-source signal synthesis** with a **natural-language outcome** (a verdict-oriented report) at a **price and speed** angels and micro-VCs can adopt.

**Gap today:** The product **shape** (scan → structured report → verdict) can exist early; **production parity** requires **data pipelines per source**, **entity resolution**, **evaluation**, **abuse/cost control**, **compliance**, and **operational reliability**—the same categories incumbents spent years and hundreds of people on.

**Where you can be better than competitors:** Not by out-PitchBooking PitchBook on **tabular coverage**, but by owning **(a)** timely **unstructured / “dirty” signals**, **(b)** **cross-source reasoning** with explicit provenance, **(c)** **time-to-answer** and **UX** for a question—not a filter panel—and **(d)** **price accessibility** for high-deal-volume users who will never buy enterprise data contracts.

**The right question:** Asking whether DealScannr “wins” on **the dimensions incumbents optimize for** (tabular depth, analyst curation, enterprise licensing, decades of brand) is **usually the wrong bar** near-term—any claim to beat them *there* would be marketing, not reality. The useful question is whether you can ship a **different product**: **answering** (verdict-oriented narrative + provenance for **one resolved entity**) in **~60 seconds**, for buyers who **never** pay $30K/year but still need more than gut instinct. That segment is **real** and **underserved**; the strategy is **sound only if the data engineering is real** (see §2).

---

## 2. Strategic reality check (unbiased)

### 2.1 Where it genuinely **cannot** beat them (near-term)

PitchBook, CB Insights, and peers sit on **years of structured data**, **analyst curation**, **enterprise relationships**, and **legal licensing** that cost **hundreds of millions** to assemble. Replicating that **tabular depth** is not a credible near-term goal; this document treats that as **honest**, not apologetic.

### 2.2 Where it has a **real shot**

Incumbents are structurally built for **browsing** (filters, tables, exports), not **terminating search** with a **decision artifact**. A GP or syndicate lead screening **dozens of deals** a week often wants **speed and narrative**, not another panel. If DealScannr can **reliably** deliver a **provenance-backed, multi-signal** view of a **specific company**—**faster and cheaper** than institutional tools—that is a **genuinely different product**, not “PitchBook lite.”

The **angel / micro-VC** wedge is also structurally real: they will **not** buy $30K/year databases at scale but still need **signal, not vibes**.

### 2.3 The honest risk this doc must **not** underplay

The **knife’s edge:** without **dedicated pipelines** (litigation, GitHub, job feeds, etc.—each with recall, freshness, and entity match), reports collapse into **better-formatted generic web synthesis**. At that point there is **no moat**: Perplexity (and peers) already do **broad web + brand + scale**; “signals” that are mostly **LLM polish over a thin crawl** are not defensible.

### 2.4 The **actual** deciding factor (the whole bet)

> **Better than a competitor in a signal lane means recall + freshness + entity match on that lane—not a paragraph that *mentions* the lane.**

Pick **2–3** lanes and aim to be **best-in-class on those pipelines** before widening the story. If that layer is **skipped** in favor of UI and narrative alone, the strategy **fails** in the market, even if the pitch deck still looks good.

**Which lanes?** That choice is **load-bearing** (build order, eval data, first users, pitch). A **working default** is in **§2.6** so the doc is not stuck in abstraction—replace it when user research says so, but do not leave “TBD” on the critical path.

### 2.5 Verdict

**Beatable in a niche, not in the broad institutional market** on their terms. The path is **sound** if **data engineering is the spine**; it is **not** sound if the product remains **synthesis without proprietary retrieval**. The doc states that; **execution** is whether retrieval is proprietary or a better-looking generic wrapper.

### 2.6 Initial wedge: **working default** (decide, validate, or replace)

Leaving “2–3 lanes” unnamed keeps sequencing and hiring **abstract**. Until research overrides this, **name the lanes**:

| Order | Lane | Why this default |
|-------|------|------------------|
| **1** | **Litigation & regulatory filings** (only where access is legal and technically sound) | Investors care disproportionately; aggregating dockets/regulators manually is slow; structurally **not** the hero table in funding databases; evidence is often **primary** (filings), which helps provenance. |
| **2** | **Engineering health** — public source control activity (e.g. GitHub/GitLab) **plus** engineering-relevant job posts | Strong fit for **tech-heavy** dealflow common among angels/syndicates; boundaries are hard but **bounded** (org/repo mapping, bot noise). |
| **3** | **One** of: **hiring breadth** (all roles → growth/pivot proxy) **or** **customer sentiment** (reviews, ranks → B2C/prosumer) | Pick **after** ~10 targeted user conversations: consumer deals → lean sentiment; infra/B2B → hiring may dominate. |

**First-line pitch this implies:** *Before the meeting, we surface **legal/regulatory risk** and **engineering reality** for **this** company—with receipts—not a generic web summary.*

**Rule:** If interviews contradict the default, **swap or reorder** lane 2/3—not the idea of **named, measured lanes**. “Everything eventually” with no first wedge blocks connectors, eval sets, and sales story the same way UI-only shipping does.

---

## 3. What “production level” means in this category

### 3.1 Dimensions (all of them matter at scale)

| Dimension | Production expectation | Why investors / legal care |
|-----------|------------------------|----------------------------|
| **Coverage** | Known universe: which companies, geos, stages; what is explicitly *not* covered | Decisions are only as good as “what we didn’t see” |
| **Freshness** | SLAs or documented refresh; stale flags on signals | DD on a moving target |
| **Correctness** | Entity resolution (same company/person across sources); dedup; disambiguation | Wrong company = catastrophic |
| **Provenance** | Every non-trivial claim traceable to source + retrieval snapshot | Audit, trust, disputes |
| **Safety** | Hallucination controls; “unknown” vs invented; preliminary vs indexed confidence | Reputational and legal risk |
| **Abuse & cost** | Auth, quotas, rate limits, bot/scrape protection, spend caps per tenant | Survival as a service |
| **Compliance** | ToS for third-party data; retention; PII handling; terms of use and disclaimers | Enterprise and EU/US exposure |
| **Reliability** | Observability, incident response, backups, DR for vector + object storage | Paying users expect uptime |
| **Workflow** | Export, sharing, teams, API, CRM/sheet hooks (even minimal) | Fits how deals actually flow |

A **demo** can skip half of this; **production** cannot—especially once money changes hands.

### 3.2 “Competitor level” by archetype

| Archetype | Examples | What “good” looks like for them |
|-----------|----------|----------------------------------|
| **Institutional databases** | PitchBook, CB Insights, (in parts) Crunchbase Pro | Deep **structured** tables, analysts, methodologies, enterprise contracts |
| **Single-signal specialists** | Harmonic (hiring), others by niche | High recall within **one** signal; clear limits elsewhere |
| **General AI search** | Perplexity, ChatGPT + browsing | Fast answers, broad web; **weak** on private-market entity fidelity and licensed baselines |

**Unbiased takeaway:** Incumbents are **strong** where DealScannr’s doc positions them (structured private markets data, sales motion, brand). They are **weak** where building **unified narrative + multi-signal synthesis + speed + price** for **non-enterprise** buyers—but only if DealScannr’s **underlying signals** are real, not only LLM-shaped paragraphs over thin web snippets.

---

## 4. Full vision: DealScannr at production (target state)

Think in **layers**. The [product doc](./DEALSCANNR_PRODUCT.md) already lists **sources** and **UX**; below is the **production** completion of that story.

### 4.1 Data & ingestion (the real moat)

- **Per-source connectors** with explicit schemas: court/filings, org/people change signals (within ToS), job postings, GitHub/GitLab public activity, podcast transcripts (where licensed or allowed), patents, app store reviews/ranks, Wayback deltas, news/press, and a **baseline** funding layer (licensed or clearly attributed public APIs).
- **Normalization pipeline:** cleaning, language detection, dedup, versioning, **ingest job id** and **as-of** timestamps on every chunk.
- **Freshness policy:** TTL per source type; re-pull rules; “last verified” in the UI.
- **Entity graph:** company ↔ people ↔ domains ↔ product names; merge/split with human-review queue for ambiguous cases.
- **Storage:** vector index (e.g. Qdrant) **plus** structured rows (events, citations) for queries that should not be “semantic guesswork.”

### 4.2 Retrieval & reasoning (trustworthy synthesis)

- **Hybrid retrieval:** structured filters + semantic search + (where justified) keyword/BM25.
- **Grounding contract:** model may only assert facts supported by retrieved evidence; otherwise **unknown** or **speculative** with lower confidence.
- **Verdict logic:** explicit rubric (what flips green/yellow/red); **preliminary** state when indexed evidence is thin (you already bias this in code—productize it).
- **Evaluation:** golden sets of companies; human-rated reports; regression on hallucination rate and entity accuracy.

### 4.3 Product surface (workflow, not only a report)

- **Accounts & teams** (even if post–v0): shared scans, annotations, PDF/export, link sharing with expiry.
- **Report history** and **diff**: “what changed since last scan” (huge for returning users).
- **API** for power users and downstream tools (CRM, Notion, internal memos).

### 4.4 Platform & operations

- **AuthN/AuthZ**, billing (Stripe), usage metering, admin dashboards.
- **Rate limiting**, queue backpressure, cost per scan visible internally.
- **Security:** SSRF boundaries on any URL fetch, secret hygiene, dependency and container scanning.
- **Observability:** traces from request → retrieval ids → LLM call; PII-safe logging.

### 4.5 Legal & go-to-market (production includes this)

- Clear **disclaimer**: not investment advice; verify primary sources.
- **Data attribution** and respect for robots/ToS per connector.
- **Sales motion** appropriate to tier: self-serve vs outbound; support SLAs for Team/Enterprise.

---

## 5. What is missing (gap vs production + vs competitors)

This is a **gap list**, not a shame list. Early repos **should** be missing most of this.

### 5.1 Relative to **institutional** competitors (PitchBook-class)

| Area | Typical incumbent strength | DealScannr gap to close |
|------|----------------------------|-------------------------|
| Structured funding & firm data | Core business | Licensed/partner data or deep Crunchbase-style APIs + clear attribution |
| Analyst curation | People-heavy | Optional: “human QA” tier—not required for v1 if eval + provenance are strong |
| Enterprise workflow | SSO, seats, contracts | Teams, billing, audit logs |
| Brand & distribution | Decades | Community wedge + proof posts (per product GTM) |

**Honest position:** You do **not** win by pretending equal **tabular depth** on day one.

### 5.2 Relative to **your own** product promise (cross-source “dirty” signals)

| Promised signal (from product doc) | Production requirement | Common early-stage gap |
|------------------------------------|------------------------|-------------------------|
| Court / litigation | Reliable docket coverage, entity match | No dedicated pipeline; web RAG only |
| LinkedIn / org changes | Stable, ToS-safe source or partnership | Scraping risk; no graph |
| Hiring velocity | Job feed + dedup by company | Single vendor or ad hoc HTML |
| GitHub activity | Org/repo resolution, bot filtering | No org-level job |
| Podcasts | Transcripts + speaker diarization + entity link | Licensing and cost |
| Patents | Assignee ↔ company mapping | USPTO/EPO pipelines |
| Reviews / rankings | Store APIs + trend baselines | Fragmented per platform |
| Wayback | Diff UX + storage | Heavy storage/compute |
| Cross-source entity resolution | Graph + eval metrics | Hardest technical moat |

### 5.3 Relative to **general AI search** (Perplexity-class)

| They have | You need to beat them **for investors** |
|-----------|----------------------------------------|
| Huge crawl + brand | **Entity-accurate** private company focus + **structured signal types** + **stale/as-of** semantics |
| Fast generic answers | **Repeatable** methodology and **exportable** report, not a one-off chat |

If reports are mostly **generic web synthesis**, you are **adjacent** to Perplexity, not clearly superior. (See **§2.3**.)

### 5.4 Engineering / ops gaps (typical from [CODEBASE_AUDIT.md](./CODEBASE_AUDIT.md) themes)

- Hardened **auth**, **rate limits**, **cost controls** for LLM + crawl.
- **Slug/company_id** consistency across ingest and API (silent empty retrieval otherwise).
- **Embedding model / vector dim** discipline across environments.
- **CI/E2E** as release gate; runbooks for dependency outages (Groq, Qdrant, Firecrawl, etc.).

---

## 6. What to add that is **genuinely better** than competitors

These are **strategic bets** where incumbents are **structurally slow** or **product-incompatible**, not a guarantee—execution and compliance still decide outcomes.

### 6.1 “Analyst memo” in 60 seconds (outcome UX)

- **One question in, one decision artifact out:** summary, signals, verdict, **click-through citations**—optimized for **pass/meeting/email forward**.
- Incumbents optimize for **browsing**; you optimize for **termination of search** (time saved is the product).

### 6.2 Unified **change detection** across sources

- **“What changed since last month?”** across hiring, filings, repo activity, reviews—surfaced as a **diff report**.
- Databases show **snapshots**; a synthesis product can own **delta narrative** if ingestion is continuous.

### 6.3 Explicit **confidence & evidence budget**

- Show **indexed vs live-only**, **chunk count**, **source diversity score**, and **known unknowns**.
- Most competitors either don’t do this or don’t do it in **investor-native** language—this is **trust UX**, not a gimmick.

### 6.4 **Angel / micro-VC** price and packaging

- **Low-friction** tier ($99–$500/mo) with generous scans vs **$30K** institutional tools.
- **Honest wedge:** users who will **never** buy PitchBook but still need **signal, not vibes**.

### 6.5 Deep **connectors** incumbents under-invest in (selective depth)

Pick **2–3** where you can be **best in class** before going wide. The doc’s **default stack** is spelled out in **§2.6** (litigation/regulatory, engineering health, then hiring *or* sentiment). Other credible lanes exist; the point is to **commit** and measure, not to keep the set open-ended.

**Better than competitor** here means **recall + freshness + entity match** on those lanes, not a paragraph that *mentions* them. (**§2.4** — this is the deciding factor.)

### 6.6 **API-first** for the long tail

- Institutional tools gate APIs and price them aggressively; a **clean JSON report API** for syndicates and solo GPs is a distribution lever.

### 6.7 **Methodology transparency** (lightweight, not academic)

- Public **methodology page**: how verdict is scored, what sources are in v1, known failure modes.
- Builds trust vs black-box chat and vs opaque vendor “scores.”

---

## 7. Sequencing recommendation (high level)

**Calendar honesty:** The steps below read fast; **shipping them does not.** The **vertical slice** (end-to-end value with **real** multi-connector citations for a **resolved** company) is usually the **hardest and longest** early chunk of work—not a “spike.” **Entity resolution**, even an MVP (domain, legal name, geo, disambiguation, failure logging, maybe a minimal review path), is routinely **weeks to multi-month** depending on team size and how hard you measure “wrong company = unacceptable.” Treat this list as **dependency order**, not implied duration.

**Interdependence:** A “slice” without entity handling is a **demo**. Plan **slice + entity** as **one track** with explicit milestones (e.g. golden set of N companies, wrong-entity rate threshold, citation checks per lane in **§2.6**).

1. **Prove one vertical slice end-to-end:** company input → report with **real citations** from **at least two independent connector classes** aligned with the **named lanes** in **§2.6** (not “any two web sources”).
2. **Entity resolution MVP** (in parallel with #1 where possible): domain + legal name + location disambiguation; log failures; define what happens when confidence is low.
3. **Eval harness:** small golden set per wedge lane; block regressions on hallucination and **wrong-entity** pulls.
4. **Production gates:** auth, rate limits, metering, disclaimers, retention policy.
5. **Expand sources** only when **freshness + provenance** for the current wedge is **honest** under review.

`TRACKER_TODO.md` Phase 5 (per-source scrapers, entity resolver, scheduler) is the **spine** of closing the gap between **narrative** and **production moat**.

---

## 8. Non-goals (to avoid distraction)

- **Replacing** licensed databases **entirely** in year one.
- **Scraping** high-risk sources without legal review.
- **Feature parity** with CB Insights “everything app” before **one** wedge is undeniable.

---

## 9. One-line internal mantra

> **Production for DealScannr = provenance-backed multi-signal answers for a *specific company entity*, faster and cheaper than institutional tools—not the same spreadsheet as PitchBook.**

---

*Last updated: 2025-03-21*
