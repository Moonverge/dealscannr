from __future__ import annotations

import logging
import os
import re
from typing import Any

from rag.embeddings import embed_query_text, embedding_vector_dim
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
from rag.prompts.synthesis import build_synthesis_messages
from rag.prompts.system import SYSTEM_PROMPT
from rag.schema.llm_report import ReportOutput, ReportSection, insufficient_validation_fallback
from rag.utils.display import format_company_display_name

GROQ_AVAILABLE = False
try:
    from groq import Groq

    GROQ_AVAILABLE = True
except Exception:
    pass

QDRANT_COLLECTION = "dealscannr_chunks"

# Lower number = earlier in synthesis context (Mongo cap). Unknown connectors sort last.
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
# Avoid treating tiny strings as "duplicate" via substring (e.g. a legal boilerplate phrase).
_MIN_SUBSTRING_DEDUPE_LEN = 200

logger = logging.getLogger(__name__)

# Product scans (scan_id != "adhoc") need enough distinct chunks before PASS/MEET/FLAG.
MIN_DISTINCT_CHUNKS_FOR_SUBSTANTIVE_VERDICT = 3

SYNTHESIS_MODELS = (
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
)
SYNTHESIS_OPENAI_MODEL = "gpt-4o-mini"
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"


def _downgrade_sections_to_preliminary(report: ReportOutput) -> ReportOutput:
    """When few indexed chunks, mark complete sections as preliminary (thin evidence)."""
    new_sections: dict[str, ReportSection] = {}
    for key, sec in report.sections.items():
        st = sec.status
        if st == "complete":
            st = "preliminary"
        new_sections[key] = ReportSection(
            text=sec.text,
            citations=list(sec.citations),
            status=st,
        )
    return report.model_copy(update={"sections": new_sections})


def _cap_verdict_when_single_evidence_chunk(
    report: ReportOutput, *, distinct_chunk_count: int
) -> ReportOutput:
    """MEET implies cross-lane substance; one synthetic/live chunk cannot support it."""
    if distinct_chunk_count != 1 or report.verdict in ("INSUFFICIENT", "FLAG"):
        return report
    if report.verdict == "MEET":
        return report.model_copy(
            update={
                "verdict": "PASS",
                "confidence_score": min(float(report.confidence_score), 0.52),
            }
        )
    return report.model_copy(
        update={"confidence_score": min(float(report.confidence_score), 0.58)}
    )


def _enforce_minimum_distinct_chunks(
    report: ReportOutput, *, distinct_chunk_count: int, scan_id: str
) -> ReportOutput:
    """Do not emit MEET/PASS/FLAG on thin evidence for real scans."""
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
    body = str(
        payload.get("normalized_text")
        or payload.get("raw_text")
        or "",
    ).strip()
    if not body and isinstance(hit, dict):
        body = str(
            hit.get("text")
            or hit.get("normalized_text")
            or hit.get("raw_text")
            or "",
        ).strip()
    return body


def _connector_priority_value(hit: Any) -> int:
    p = _payload_from_hit(hit)
    cid = str(p.get("connector_id") or "").strip()
    return CONNECTOR_PRIORITY.get(cid, _DEFAULT_CONNECTOR_PRIORITY)


def _prioritize_and_dedupe_hits(hits: list[Any], *, max_k: int = 40) -> list[Any]:
    """Sort Mongo/Qdrant-shaped hits by connector priority, drop obvious substring duplicates, cap."""
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
            if len(shorter) < _MIN_SUBSTRING_DEDUPE_LEN:
                continue
            if len(shorter) == len(longer):
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
        self._client: Any = None
        if GROQ_AVAILABLE and self.groq_api_key:
            self._client = Groq(api_key=self.groq_api_key)

    def _embed(self, text: str) -> list[float] | None:
        return embed_query_text(
            text,
            openai_api_key=self.openai_api_key,
            together_api_key=self.together_api_key,
            nomic_api_key=self.nomic_api_key,
        )

    def _usage_from_completion(self, comp: Any, usage: dict[str, int]) -> None:
        u = getattr(comp, "usage", None)
        if u is not None:
            usage["prompt_tokens"] = int(getattr(u, "prompt_tokens", 0) or 0)
            usage["completion_tokens"] = int(getattr(u, "completion_tokens", 0) or 0)

    def _complete(
        self,
        system: str,
        user: str,
        models: tuple[str, ...] = SYNTHESIS_MODELS,
        *,
        json_mode: bool = False,
    ) -> tuple[str, dict[str, int]]:
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        _user = messages[1]["content"]
        logger.info(
            "synthesis_prompt_preview system_len=%s user_len=%s user_first_500=%r user_last_500=%r",
            len(messages[0]["content"]),
            len(_user),
            _user[:500],
            _user[-500:],
        )
        oai_key = (self.openai_api_key or "").strip()
        use_openai_first = self.llm_provider != "groq" and bool(oai_key)

        if use_openai_first:
            try:
                from openai import OpenAI

                oclient = OpenAI(api_key=oai_key)
                kwargs: dict[str, Any] = {
                    "model": SYNTHESIS_OPENAI_MODEL,
                    "messages": messages,
                    "max_tokens": 4000,
                    "temperature": 0.1,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                comp = oclient.chat.completions.create(**kwargs)
                text = (comp.choices[0].message.content or "").strip()
                self._usage_from_completion(comp, usage)
                if text:
                    return text, usage
            except Exception as openai_err:
                logger.warning("openai_chat_failed err_type=%s", type(openai_err).__name__)

        if not GROQ_AVAILABLE or not self._client:
            return "", usage
        seen: set[str] = set()
        groq_models: list[str] = []
        for m in (GROQ_FALLBACK_MODEL,) + tuple(models):
            if m not in seen:
                seen.add(m)
                groq_models.append(m)
        last_err: Exception | None = None
        for model in groq_models:
            try:
                comp = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=4000 if model == GROQ_FALLBACK_MODEL else 8000,
                )
                text = (comp.choices[0].message.content or "").strip()
                self._usage_from_completion(comp, usage)
                if text:
                    return text, usage
            except Exception as e:
                last_err = e
                logger.warning("groq_chat_failed model=%s err_type=%s", model, type(e).__name__)
        if last_err:
            logger.warning("groq_chat_all_models_failed: %s", last_err)
        return "", usage

    def run(
        self,
        query: str,
        *,
        scan_id: str = "adhoc",
        entity_id: str = "adhoc",
        allow_live_fallback: bool = True,
        mongo_evidence_hits: list[dict[str, Any]] | None = None,
        domain: str = "",
    ) -> tuple[ReportOutput, int, dict[str, int]]:
        parsed = parse_query(query)
        company_name = parsed.entity or "Unknown Company"
        slug = _slug(company_name)

        vdim = (
            embedding_vector_dim(
                self.openai_api_key,
                self.together_api_key,
                self.nomic_api_key,
            )
            or 1536
        )
        embedding = self._embed(f"{company_name} {query}")
        if scan_id != "adhoc":
            sid = str(scan_id)
            eid = str(entity_id)
            logger.info(
                "qdrant_retrieve_attempt scan_id=%s entity_id=%s collection=%s limit=40",
                sid,
                eid,
                QDRANT_COLLECTION,
            )
            chunks = retrieve_chunks(
                self.qdrant_url,
                QDRANT_COLLECTION,
                embedding,
                None,
                limit=40,
                vector_size=vdim,
                scan_id=sid,
                qdrant_api_key=self.qdrant_api_key,
            )
            logger.info("qdrant_retrieve_result scan_id=%s hits_count=%s", sid, len(chunks))
            if not chunks:
                logger.warning(
                    "qdrant_scan_id_miss_trying_entity scan_id=%s entity_id=%s",
                    sid,
                    eid,
                )
                chunks = retrieve_chunks(
                    self.qdrant_url,
                    QDRANT_COLLECTION,
                    embedding,
                    None,
                    limit=40,
                    vector_size=vdim,
                    entity_id=eid,
                    qdrant_api_key=self.qdrant_api_key,
                )
                logger.info("qdrant_retrieve_result entity_id=%s hits_count=%s", eid, len(chunks))
            if not chunks:
                chunks = retrieve_chunks(
                    self.qdrant_url,
                    QDRANT_COLLECTION,
                    embedding,
                    slug,
                    limit=20,
                    vector_size=vdim,
                    qdrant_api_key=self.qdrant_api_key,
                )
                logger.info(
                    "qdrant_retrieve_result company_slug=%s hits_count=%s",
                    slug,
                    len(chunks),
                )
            if mongo_evidence_hits and len(chunks) < 3:
                logger.warning(
                    "qdrant_thin_using_mongo_evidence scan_id=%s qdrant_hits=%s mongo_hits=%s",
                    sid,
                    len(chunks),
                    len(mongo_evidence_hits),
                )
                chunks = mongo_evidence_hits[:40]
            top_k = 40
        else:
            chunks = retrieve_chunks(
                self.qdrant_url,
                QDRANT_COLLECTION,
                embedding,
                slug,
                limit=20,
                vector_size=vdim,
                qdrant_api_key=self.qdrant_api_key,
            )
            top_k = 8
        top_chunks = rerank(chunks, top_k=top_k)

        live_urls: list[str] = []
        live_body = ""
        if not top_chunks and allow_live_fallback:
            live_body, live_urls = fetch_live_context(
                company_name,
                self.firecrawl_api_key,
            )

        # Pipeline passes mongo_evidence_hits (full ingest set). Prefer it for synthesis so the LLM
        # sees the same chunks as the test script, not only whatever Qdrant vector search returns.
        labeling_hits: list[Any] | None = None
        if mongo_evidence_hits:
            labeling_hits = _prioritize_and_dedupe_hits(list(mongo_evidence_hits), max_k=40)
        elif top_chunks:
            labeling_hits = list(top_chunks)

        if labeling_hits:
            labeled_evidence, chunk_ids = labeled_blocks_from_qdrant_hits(
                labeling_hits,
                scan_id=scan_id,
            )
        elif live_body:
            labeled_evidence, chunk_ids = labeled_block_from_live_snapshot(
                live_body,
                live_urls,
                scan_id=scan_id,
            )
        else:
            labeled_evidence, chunk_ids = labeled_block_from_empty_state(
                company_name,
                scan_id=scan_id,
            )

        logger.info(
            "synthesis_context_preview scan_id=%s chunk_id_count=%s evidence_chars=%s first_200=%r",
            scan_id,
            len(chunk_ids),
            len(labeled_evidence),
            labeled_evidence[:200],
        )

        valid_chunk_ids = set(chunk_ids)
        if labeling_hits:
            signal_lane_count = distinct_connector_count_from_hits(labeling_hits)
        elif live_body:
            signal_lane_count = 1
        else:
            signal_lane_count = 0
        indexed_for_prompt = len(labeling_hits) if labeling_hits else 0
        messages = build_synthesis_messages(
            format_company_display_name(company_name),
            query=query,
            labeled_evidence=labeled_evidence,
            chunk_ids=chunk_ids,
            indexed_chunk_count=indexed_for_prompt,
            signal_lane_count=signal_lane_count,
            live_web_urls=live_urls if live_body else None,
            domain=domain,
        )
        raw_synthesis, llm_usage = self._complete(
            messages[0]["content"],
            messages[1]["content"],
            SYNTHESIS_MODELS,
            json_mode=True,
        )

        if not raw_synthesis:
            rep = self._mock_report_output(
                has_key=bool(self.groq_api_key or (self.openai_api_key or "").strip()),
            )
            return rep, 0, llm_usage

        report, hallucinated = parse_validate_report_output(raw_synthesis, valid_chunk_ids)
        report = report.model_copy(update={"chunk_count": len(valid_chunk_ids)})
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
            report,
            distinct_chunk_count=len(valid_chunk_ids),
            scan_id=scan_id,
        )
        return report, hallucinated, llm_usage

    def _mock_report_output(self, *, has_key: bool = False) -> ReportOutput:
        if not has_key:
            return insufficient_validation_fallback(
                parse_error="OPENAI_API_KEY and/or GROQ_API_KEY missing; add a key to .env and restart API.",
            )
        return insufficient_validation_fallback(
            parse_error="LLM returned no usable text (OpenAI/Groq error, quota, or empty completion).",
        )
