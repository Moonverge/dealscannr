"""RAG Engine: retrieve → rerank → two-pass synthesis → scoring → report."""

from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from rag.embeddings import embed_query_text, embedding_vector_dim
from rag.pipeline.cache import (
    EMBEDDING_TTL,
    REPORT_TTL,
    cache_get,
    cache_set,
    report_cache_key,
)
from rag.pipeline.chunk_context import (
    _payload_from_hit,
    distinct_connector_count_from_hits,
    labeled_block_from_empty_state,
    labeled_block_from_live_snapshot,
    labeled_blocks_from_qdrant_hits,
)
from rag.pipeline.llm_report_output import parse_validate_report_output
from rag.pipeline.query_parser import parse_query
from rag.pipeline.reranker import rerank
from rag.pipeline.retriever import retrieve_chunks
from rag.pipeline.live_context import fetch_live_context
from rag.prompts.synthesis import (
    build_synthesis_messages,
    build_section_messages,
    build_verdict_messages,
)
from rag.prompts.system import SYSTEM_PROMPT
from rag.schema.llm_report import (
    DEFAULT_DISCLAIMER,
    REPORT_SECTION_KEYS,
    ReportOutput,
    ReportSection,
    insufficient_validation_fallback,
)
from rag.utils.display import format_company_display_name

GROQ_AVAILABLE = False
try:
    from groq import Groq

    GROQ_AVAILABLE = True
except Exception:
    pass

logger = logging.getLogger(__name__)

QDRANT_COLLECTION = "dealscannr_chunks"

# ── Model configuration ────────────────────────────────────────────────

SYNTHESIS_OPENAI_MODEL = "gpt-4o"
GROQ_PRIMARY_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"

GROQ_JSON_ENFORCEMENT = (
    "\n\nYou must respond with valid JSON only. No markdown. "
    "No explanation. No code fences. Start with { and end with }."
)

# ── Connector priority + dedup ─────────────────────────────────────────

CONNECTOR_PRIORITY: dict[str, int] = {
    "sec_10k_risk_factors": 1,
    "wikipedia": 2,
    "sec_edgar": 3,
    "courtlistener": 4,
    "github_connector": 5,
    "news_connector": 6,
    "hiring_connector": 7,
}
_DEFAULT_CONNECTOR_PRIORITY = 50
_MIN_SUBSTRING_DEDUPE_LEN = 200

MIN_DISTINCT_CHUNKS_FOR_SUBSTANTIVE_VERDICT = 3


# ── Post-processing helpers (preserved) ────────────────────────────────


def _downgrade_sections_to_preliminary(report: ReportOutput) -> ReportOutput:
    new_sections: dict[str, ReportSection] = {}
    for key, sec in report.sections.items():
        st = "preliminary" if sec.status == "complete" else sec.status
        new_sections[key] = ReportSection(text=sec.text, citations=list(sec.citations), status=st)
    return report.model_copy(update={"sections": new_sections})


def _cap_verdict_when_single_evidence_chunk(
    report: ReportOutput, *, distinct_chunk_count: int
) -> ReportOutput:
    if distinct_chunk_count != 1 or report.verdict in ("INSUFFICIENT", "FLAG"):
        return report
    if report.verdict == "MEET":
        return report.model_copy(
            update={"verdict": "PASS", "confidence_score": min(float(report.confidence_score), 0.52)}
        )
    return report.model_copy(update={"confidence_score": min(float(report.confidence_score), 0.58)})


def _enforce_minimum_distinct_chunks(
    report: ReportOutput, *, distinct_chunk_count: int, scan_id: str
) -> ReportOutput:
    if scan_id == "adhoc":
        return report
    if distinct_chunk_count >= MIN_DISTINCT_CHUNKS_FOR_SUBSTANTIVE_VERDICT:
        return report
    if report.verdict == "INSUFFICIENT":
        return report
    reason = (
        f"Verdict forced to INSUFFICIENT: fewer than {MIN_DISTINCT_CHUNKS_FOR_SUBSTANTIVE_VERDICT} "
        "distinct evidence chunks for this scan (DealScannr policy)."
    )
    ku = [reason, *list(report.known_unknowns)]
    return report.model_copy(
        update={
            "verdict": "INSUFFICIENT",
            "confidence_score": min(float(report.confidence_score), 0.35),
            "lane_coverage": 0,
            "known_unknowns": ku[:24],
            "chunk_count": distinct_chunk_count,
        }
    )


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "unknown"


def _normalized_body_from_hit(hit: Any) -> str:
    payload = _payload_from_hit(hit)
    body = str(payload.get("normalized_text") or payload.get("raw_text") or "").strip()
    if not body and isinstance(hit, dict):
        body = str(hit.get("text") or hit.get("normalized_text") or hit.get("raw_text") or "").strip()
    return body


def _connector_priority_value(hit: Any) -> int:
    p = _payload_from_hit(hit)
    cid = str(p.get("connector_id") or "").strip()
    return CONNECTOR_PRIORITY.get(cid, _DEFAULT_CONNECTOR_PRIORITY)


def _prioritize_and_dedupe_hits(hits: list[Any], *, max_k: int = 40) -> list[Any]:
    if not hits:
        return []
    indexed = list(enumerate(hits))
    indexed.sort(key=lambda pair: (_connector_priority_value(pair[1]), pair[0]))
    sorted_hits = [h for _, h in indexed]
    kept: list[Any] = []
    for h in sorted_hits:
        t = _normalized_body_from_hit(h)
        if not t:
            continue
        skip_new = False
        remove_indices: list[int] = []
        for i, k in enumerate(kept):
            kt = _normalized_body_from_hit(k)
            if not kt:
                continue
            if t == kt:
                skip_new = True
                break
            shorter, longer = (t, kt) if len(t) <= len(kt) else (kt, t)
            if len(shorter) < _MIN_SUBSTRING_DEDUPE_LEN or len(shorter) == len(longer):
                continue
            if shorter not in longer:
                continue
            if len(t) < len(kt):
                skip_new = True
                break
            remove_indices.append(i)
        if skip_new:
            continue
        for i in sorted(remove_indices, reverse=True):
            del kept[i]
        kept.append(h)
    return kept[:max_k]


# ── RAG Engine ─────────────────────────────────────────────────────────


class RAGEngine:
    def __init__(
        self,
        groq_api_key: str | None = None,
        qdrant_url: str | None = None,
        qdrant_api_key: str | None = None,
        openai_api_key: str | None = None,
        together_api_key: str | None = None,
        nomic_api_key: str | None = None,
        firecrawl_api_key: str | None = None,
        llm_provider: str | None = None,
    ):
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        self.qdrant_url = qdrant_url or os.environ.get("QDRANT_URL")
        self.qdrant_api_key = qdrant_api_key or os.environ.get("QDRANT_API_KEY")
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.llm_provider = (llm_provider or os.environ.get("LLM_PROVIDER") or "openai").strip().lower()
        self.together_api_key = together_api_key or os.environ.get("TOGETHER_API_KEY")
        self.nomic_api_key = nomic_api_key or os.environ.get("NOMIC_API_KEY")
        self.firecrawl_api_key = firecrawl_api_key or os.environ.get("FIRECRAWL_API_KEY")
        self._groq_client: Any = None
        if GROQ_AVAILABLE and self.groq_api_key:
            self._groq_client = Groq(api_key=self.groq_api_key)

    # ── Embedding ──────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float] | None:
        return embed_query_text(
            text,
            openai_api_key=self.openai_api_key,
            together_api_key=self.together_api_key,
            nomic_api_key=self.nomic_api_key,
        )

    # ── LLM completion chain ──────────────────────────────────────────

    def _usage_from_completion(self, comp: Any, usage: dict[str, int]) -> None:
        u = getattr(comp, "usage", None)
        if u is not None:
            usage["prompt_tokens"] = int(getattr(u, "prompt_tokens", 0) or 0)
            usage["completion_tokens"] = int(getattr(u, "completion_tokens", 0) or 0)

    def _complete_openai(
        self, system: str, user: str, *, json_mode: bool = True
    ) -> tuple[str, dict[str, int]]:
        """Primary: gpt-4o via OpenAI with instructor-wrapped JSON mode."""
        oai_key = (self.openai_api_key or "").strip()
        if not oai_key:
            raise RuntimeError("no openai key")
        import instructor
        from openai import OpenAI

        raw_client = OpenAI(api_key=oai_key)
        client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)
        kwargs: dict[str, Any] = {
            "model": SYNTHESIS_OPENAI_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": 4000,
            "temperature": 0.1,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        comp = client.client.chat.completions.create(**kwargs)
        text = (comp.choices[0].message.content or "").strip()
        usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
        self._usage_from_completion(comp, usage)
        if text:
            return text, usage
        raise RuntimeError("openai_empty_response")

    def _complete_groq(
        self,
        system: str,
        user: str,
        *,
        model: str = GROQ_PRIMARY_MODEL,
    ) -> tuple[str, dict[str, int]]:
        """Groq fallback with JSON enforcement in system prompt + retry."""
        if not GROQ_AVAILABLE or not self._groq_client:
            raise RuntimeError("groq unavailable")
        enforced_system = system + GROQ_JSON_ENFORCEMENT
        max_tokens = 4000 if model == GROQ_FALLBACK_MODEL else 8000
        usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}

        for attempt in range(2):
            comp = self._groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": enforced_system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            text = (comp.choices[0].message.content or "").strip()
            self._usage_from_completion(comp, usage)
            if not text:
                continue
            try:
                json.loads(text if not text.startswith("```") else text.split("```json")[-1].split("```")[0])
                return text, usage
            except (json.JSONDecodeError, ValueError, IndexError):
                if attempt == 0:
                    logger.warning("groq_json_retry model=%s attempt=%d", model, attempt)
                    continue
                return text, usage
        raise RuntimeError(f"groq_{model}_empty")

    def _complete(
        self, system: str, user: str, *, json_mode: bool = True
    ) -> tuple[str, dict[str, int]]:
        """Full provider chain: gpt-4o → Groq 70b → Groq 8b. Silent fallback."""
        usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
        _user = user
        logger.info(
            "synthesis_prompt_preview system_len=%s user_len=%s user_first_500=%r user_last_500=%r",
            len(system), len(_user), _user[:500], _user[-500:],
        )

        oai_key = (self.openai_api_key or "").strip()
        if self.llm_provider != "groq" and oai_key:
            try:
                return self._complete_openai(system, user, json_mode=json_mode)
            except Exception as e:
                logger.warning("openai_fallthrough: %s", type(e).__name__)

        for model in (GROQ_PRIMARY_MODEL, GROQ_FALLBACK_MODEL):
            try:
                return self._complete_groq(system, user, model=model)
            except Exception as e:
                logger.warning("groq_fallthrough model=%s: %s", model, type(e).__name__)

        return "", usage

    # ── Two-pass synthesis ─────────────────────────────────────────────

    def _complete_section(
        self,
        section_key: str,
        company_name: str,
        labeled_evidence: str,
        chunk_ids: list[str],
        domain: str,
    ) -> tuple[str, ReportSection, dict[str, int]]:
        msgs = build_section_messages(section_key, company_name, labeled_evidence, chunk_ids, domain)
        raw, usage = self._complete(msgs[0]["content"], msgs[1]["content"], json_mode=True)
        if raw:
            try:
                data = json.loads(raw if not raw.startswith("```") else raw.split("```json")[-1].split("```")[0])
                section = ReportSection(**data)
                return section_key, section, usage
            except Exception:
                pass
        fallback = ReportSection(text="Insufficient data.", citations=[], status="insufficient")
        return section_key, fallback, usage

    def _two_pass_synthesis(
        self,
        company_name: str,
        query: str,
        labeled_evidence: str,
        chunk_ids: list[str],
        signal_lane_count: int,
        domain: str,
        live_urls: list[str] | None,
    ) -> tuple[ReportOutput, int, dict[str, int]]:
        """Pass 1: sections in parallel. Pass 2: verdict synthesis."""
        total_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
        sections: dict[str, ReportSection] = {}

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(
                    self._complete_section, key, company_name, labeled_evidence, chunk_ids, domain
                ): key
                for key in REPORT_SECTION_KEYS
            }
            for future in as_completed(futures):
                try:
                    key, section, usage = future.result()
                    sections[key] = section
                    total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                except Exception as e:
                    key = futures[future]
                    logger.warning("section_synthesis_failed key=%s: %s", key, e)
                    sections[key] = ReportSection(
                        text="Insufficient data.", citations=[], status="insufficient"
                    )

        sections_for_verdict = {
            k: {"text": s.text, "citations": list(s.citations), "status": s.status}
            for k, s in sections.items()
        }
        msgs = build_verdict_messages(
            sections_for_verdict, company_name, len(chunk_ids), signal_lane_count, domain
        )
        raw_verdict, v_usage = self._complete(msgs[0]["content"], msgs[1]["content"], json_mode=True)
        total_usage["prompt_tokens"] += v_usage.get("prompt_tokens", 0)
        total_usage["completion_tokens"] += v_usage.get("completion_tokens", 0)

        if not raw_verdict:
            raise RuntimeError("verdict_synthesis_empty")

        try:
            vdata = json.loads(
                raw_verdict
                if not raw_verdict.startswith("```")
                else raw_verdict.split("```json")[-1].split("```")[0]
            )
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"verdict_json_parse: {e}") from e

        report = ReportOutput(
            verdict=vdata.get("verdict", "INSUFFICIENT"),
            confidence_score=vdata.get("confidence_score", 0.0),
            lane_coverage=vdata.get("lane_coverage", 0),
            chunk_count=len(chunk_ids),
            risk_triage=vdata.get("risk_triage", "unknown"),
            probe_questions=vdata.get("probe_questions", []),
            sections=sections,
            known_unknowns=vdata.get("known_unknowns", []),
            disclaimer=vdata.get("disclaimer", DEFAULT_DISCLAIMER),
        )

        all_citations = set()
        for sec in sections.values():
            all_citations.update(sec.citations)
        valid_ids = set(chunk_ids)
        hallucinated = len(all_citations - valid_ids)

        return report, hallucinated, total_usage

    def _single_pass_synthesis(
        self,
        company_name: str,
        query: str,
        labeled_evidence: str,
        chunk_ids: list[str],
        indexed_for_prompt: int,
        signal_lane_count: int,
        domain: str,
        live_urls: list[str] | None,
    ) -> tuple[ReportOutput, int, dict[str, int]]:
        """Original single-call fallback."""
        messages = build_synthesis_messages(
            format_company_display_name(company_name),
            query=query,
            labeled_evidence=labeled_evidence,
            chunk_ids=chunk_ids,
            indexed_chunk_count=indexed_for_prompt,
            signal_lane_count=signal_lane_count,
            live_web_urls=live_urls if live_urls else None,
            domain=domain,
        )
        raw, llm_usage = self._complete(
            messages[0]["content"], messages[1]["content"], json_mode=True
        )
        if not raw:
            rep = self._mock_report_output(
                has_key=bool(self.groq_api_key or (self.openai_api_key or "").strip())
            )
            return rep, 0, llm_usage

        valid_ids = set(chunk_ids)
        report, hallucinated = parse_validate_report_output(raw, valid_ids)
        report = report.model_copy(update={"chunk_count": len(valid_ids)})
        return report, hallucinated, llm_usage

    # ── Scoring reconciliation ─────────────────────────────────────────

    def _scoring_reconcile(
        self, report: ReportOutput, labeled_evidence: str, chunk_ids: list[str]
    ) -> ReportOutput:
        """Second-pass scoring to validate verdict. Silent on failure."""
        try:
            from rag.prompts.scoring import reconcile_verdicts, scoring_prompt

            exec_text = report.sections.get("executive_summary")
            summary = (exec_text.text if exec_text else "") or ""
            signals = json.dumps(
                {
                    "verdict": report.verdict,
                    "confidence": float(report.confidence_score),
                    "lane_coverage": report.lane_coverage,
                    "chunk_count": report.chunk_count,
                    "risk_triage": report.risk_triage,
                },
                indent=2,
            )
            preliminary = report.chunk_count < MIN_DISTINCT_CHUNKS_FOR_SUBSTANTIVE_VERDICT
            user_prompt = scoring_prompt(summary, signals, preliminary=preliminary)
            raw, _ = self._complete(SYSTEM_PROMPT, user_prompt, json_mode=True)
            if not raw:
                return report

            scoring_data = json.loads(
                raw if not raw.startswith("```") else raw.split("```json")[-1].split("```")[0]
            )
            scoring_verdict = scoring_data.get("verdict", "yellow")
            scoring_conf = float(scoring_data.get("confidence", 0.5))

            final_verdict, final_conf, needs_review = reconcile_verdicts(
                report.verdict, scoring_verdict, float(report.confidence_score), scoring_conf
            )

            updates: dict[str, Any] = {}
            if final_verdict != report.verdict:
                updates["verdict"] = final_verdict
                logger.info(
                    "scoring_adjusted_verdict from=%s to=%s needs_review=%s",
                    report.verdict, final_verdict, needs_review,
                )
            if final_conf != float(report.confidence_score):
                updates["confidence_score"] = final_conf
            if needs_review:
                ku = list(report.known_unknowns) + [
                    "Scoring pass flagged verdict conflict — manual review recommended."
                ]
                updates["known_unknowns"] = ku[:24]
            if updates:
                report = report.model_copy(update=updates)
        except Exception as e:
            logger.warning("scoring_reconcile_skipped: %s", e)
        return report

    # ── Main entry point ───────────────────────────────────────────────

    def run(
        self,
        query: str,
        *,
        scan_id: str = "adhoc",
        entity_id: str = "adhoc",
        allow_live_fallback: bool = True,
        mongo_evidence_hits: list[dict[str, Any]] | None = None,
        domain: str = "",
        scan_created_at: datetime | None = None,
    ) -> tuple[ReportOutput, int, dict[str, int]]:
        parsed = parse_query(query)
        company_name = parsed.entity or "Unknown Company"
        slug = _slug(company_name)

        # ── Report cache check ─────────────────────────────────────────
        if scan_id != "adhoc":
            cached = cache_get(report_cache_key(slug))
            if cached:
                try:
                    report = ReportOutput(**cached)
                    logger.info("report_cache_hit slug=%s scan_id=%s", slug, scan_id)
                    return report, 0, {"prompt_tokens": 0, "completion_tokens": 0}
                except Exception:
                    pass

        # ── Semantic query embedding (#3) ──────────────────────────────
        vdim = (
            embedding_vector_dim(
                self.openai_api_key, self.together_api_key, self.nomic_api_key
            )
            or 1536
        )
        embed_query = (
            f"due diligence report for {company_name}: "
            "legal risks, SEC filings, litigation history, "
            "funding rounds, hiring signals, engineering health"
        )
        embedding = self._embed(embed_query)

        # ── Retrieval with scan-age routing (#5) ───────────────────────
        scan_age_seconds = 9999.0
        if scan_created_at is not None:
            now = datetime.now(timezone.utc)
            if scan_created_at.tzinfo is None:
                scan_created_at = scan_created_at.replace(tzinfo=timezone.utc)
            scan_age_seconds = (now - scan_created_at).total_seconds()

        fresh_scan = scan_age_seconds < 60

        if scan_id != "adhoc" and fresh_scan and mongo_evidence_hits:
            chunks = mongo_evidence_hits[:40]
            logger.info("retrieval_mongo_first scan_id=%s age=%.1fs", scan_id, scan_age_seconds)
        elif scan_id != "adhoc":
            sid = str(scan_id)
            eid = str(entity_id)
            chunks = retrieve_chunks(
                self.qdrant_url, QDRANT_COLLECTION, embedding, None,
                limit=40, vector_size=vdim, scan_id=sid, qdrant_api_key=self.qdrant_api_key,
            )
            if not chunks:
                chunks = retrieve_chunks(
                    self.qdrant_url, QDRANT_COLLECTION, embedding, None,
                    limit=40, vector_size=vdim, entity_id=eid, qdrant_api_key=self.qdrant_api_key,
                )
            if not chunks:
                chunks = retrieve_chunks(
                    self.qdrant_url, QDRANT_COLLECTION, embedding, slug,
                    limit=20, vector_size=vdim, qdrant_api_key=self.qdrant_api_key,
                )
            if mongo_evidence_hits and len(chunks) < 3:
                logger.warning("qdrant_thin_using_mongo scan_id=%s qdrant=%d mongo=%d",
                               sid, len(chunks), len(mongo_evidence_hits))
                chunks = mongo_evidence_hits[:40]
            top_k = 40
        else:
            chunks = retrieve_chunks(
                self.qdrant_url, QDRANT_COLLECTION, embedding, slug,
                limit=20, vector_size=vdim, qdrant_api_key=self.qdrant_api_key,
            )
            top_k = 8

        # ── Rerank with Cohere → Jina → FlashRank (#2) ────────────────
        rerank_query = f"{company_name} due diligence legal regulatory engineering hiring"
        top_chunks = rerank(chunks, top_k=top_k, query=rerank_query)

        # ── Live fallback ──────────────────────────────────────────────
        live_urls: list[str] = []
        live_body = ""
        if not top_chunks and allow_live_fallback:
            live_body, live_urls = fetch_live_context(company_name, self.firecrawl_api_key)

        # ── Build labeled evidence ─────────────────────────────────────
        labeling_hits: list[Any] | None = None
        if mongo_evidence_hits:
            labeling_hits = _prioritize_and_dedupe_hits(list(mongo_evidence_hits), max_k=40)
        elif top_chunks:
            labeling_hits = list(top_chunks)

        if labeling_hits:
            labeled_evidence, chunk_ids = labeled_blocks_from_qdrant_hits(
                labeling_hits, scan_id=scan_id
            )
        elif live_body:
            labeled_evidence, chunk_ids = labeled_block_from_live_snapshot(
                live_body, live_urls, scan_id=scan_id
            )
        else:
            labeled_evidence, chunk_ids = labeled_block_from_empty_state(
                company_name, scan_id=scan_id
            )

        logger.info(
            "synthesis_context scan_id=%s chunk_ids=%d evidence_chars=%d",
            scan_id, len(chunk_ids), len(labeled_evidence),
        )

        valid_chunk_ids = set(chunk_ids)
        signal_lane_count = (
            distinct_connector_count_from_hits(labeling_hits)
            if labeling_hits
            else (1 if live_body else 0)
        )
        indexed_for_prompt = len(labeling_hits) if labeling_hits else 0

        # ── Synthesis: try two-pass, fallback to single-pass (#11) ─────
        try:
            report, hallucinated, llm_usage = self._two_pass_synthesis(
                company_name, query, labeled_evidence, chunk_ids,
                signal_lane_count, domain, live_urls if live_body else None,
            )
            logger.info("synthesis_mode=two_pass scan_id=%s", scan_id)
        except Exception as e:
            logger.warning("two_pass_failed_single_pass_fallback: %s", e)
            report, hallucinated, llm_usage = self._single_pass_synthesis(
                company_name, query, labeled_evidence, chunk_ids,
                indexed_for_prompt, signal_lane_count, domain,
                live_urls if live_body else None,
            )

        # ── Scoring reconciliation (#7) ────────────────────────────────
        report = self._scoring_reconcile(report, labeled_evidence, chunk_ids)

        # ── Post-processing (preserved) ────────────────────────────────
        report = _cap_verdict_when_single_evidence_chunk(
            report, distinct_chunk_count=len(valid_chunk_ids)
        )
        if (
            scan_id != "adhoc"
            and len(chunk_ids) < 5
            and report.verdict not in ("INSUFFICIENT", "FLAG")
        ):
            report = _downgrade_sections_to_preliminary(report)
        report = _enforce_minimum_distinct_chunks(
            report, distinct_chunk_count=len(valid_chunk_ids), scan_id=scan_id
        )

        # ── Cache result (#9) ──────────────────────────────────────────
        if scan_id != "adhoc" and report.verdict != "INSUFFICIENT":
            try:
                cache_set(
                    report_cache_key(slug),
                    report.model_dump(mode="python"),
                    ttl_seconds=REPORT_TTL,
                )
            except Exception:
                pass

        return report, hallucinated, llm_usage

    def _mock_report_output(self, *, has_key: bool = False) -> ReportOutput:
        if not has_key:
            return insufficient_validation_fallback(
                parse_error="OPENAI_API_KEY and/or GROQ_API_KEY missing; add a key to .env and restart API.",
            )
        return insufficient_validation_fallback(
            parse_error="LLM returned no usable text (OpenAI/Groq error, quota, or empty completion).",
        )
