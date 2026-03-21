"""PDF export via WeasyPrint — styled to match DealScannr web (packages/web/src/index.css)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from rag.schema.llm_report import ReportOutput

from bson import Binary

# Bump when PDF HTML/CSS theme changes so cached PDFs regenerate on next download.
PDF_STYLE_VERSION = "ds-light-v4"

_CHUNK_BRACKET_RE = re.compile(r"\[chunk_id:\s*([a-fA-F0-9]+)\]", re.IGNORECASE)

# Design tokens aligned with packages/web/src/index.css (:root)
C_BG = "#f8fafc"
C_SURFACE = "#ffffff"
C_BORDER = "#e2e8f0"
C_TEXT = "#0f172a"
C_TEXT_MUTED = "#64748b"
C_TEXT_SUBTLE = "#94a3b8"
C_ACCENT = "#0f766e"
C_SURFACE2 = "#f1f5f9"
C_NOTICE_BG = "#fffbeb"
C_NOTICE_BORDER = "#fcd34d"
C_NOTICE_TEXT = "#78350f"


def _verdict_badge_style(verdict: str) -> tuple[str, str, str]:
    """(text_color, background, border) — matches web VerdictBadge."""
    u = (verdict or "").upper()
    if "PRELIMINARY" in u:
        return "#7c3aed", "#f5f3ff", "#c4b5fd"
    if "MEET" in u:
        return "#059669", "#ecfdf5", "#6ee7b7"
    if "PASS" in u:
        return "#d97706", "#fffbeb", "#fcd34d"
    if "FLAG" in u:
        return "#dc2626", "#fef2f2", "#fecaca"
    if "INSUFFICIENT" in u:
        return C_TEXT_MUTED, C_SURFACE2, C_BORDER
    return C_TEXT_MUTED, C_SURFACE2, C_BORDER


def _report_content_hash(report: ReportOutput) -> str:
    payload = report.model_dump(mode="json")
    raw = json.dumps(
        {"pdf_style": PDF_STYLE_VERSION, "report": payload},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _risk_triage_line(rt: str) -> str:
    u = (rt or "unknown").strip().lower()
    if u == "clean":
        return "Risk triage: CLEAN — no material adverse signals surfaced in indexed sources."
    if u == "watch":
        return "Risk triage: WATCH — signals worth monitoring."
    if u == "flag":
        return "Risk triage: FLAG — material adverse signals in evidence."
    return "Risk triage: UNKNOWN — insufficient data to assess."


def _escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _collect_hex_chunk_ids(s: str) -> list[str]:
    return _CHUNK_BRACKET_RE.findall(s or "")


def _merge_citation_display_order(base: list[str], extra_lines: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for c in base:
        cid = (c or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        merged.append(cid)
    for line in extra_lines:
        for cid in _collect_hex_chunk_ids(line):
            if cid not in seen:
                seen.add(cid)
                merged.append(cid)
    return merged


def _normalize_chunk_id_refs(text: str, citations: list[str]) -> str:
    t = text or ""
    for i, raw in enumerate(citations):
        cid = (raw or "").strip()
        if not cid:
            continue
        t = re.sub(
            rf"\[chunk_id:\s*{re.escape(cid)}\]",
            f"[{i + 1}]",
            t,
            flags=re.IGNORECASE,
        )
    return t


def _html_body_with_inline_cites(body_norm: str, start_fn: int, num_cites: int) -> str:
    """Turn [1], [2] into superscript links to #fn{global} (local i -> start_fn + i - 1)."""
    out: list[str] = []
    for part in re.split(r"(\[\d+\])", body_norm):
        m = re.fullmatch(r"\[(\d+)\]", part)
        if m:
            loc = int(m.group(1))
            if 1 <= loc <= num_cites:
                g = start_fn + loc - 1
                out.append(
                    f'<sup class="cite-ref"><a href="#fn{g}">{loc}</a></sup>'
                )
            else:
                out.append(_escape(part))
        else:
            out.append(_escape(part))
    return "".join(out)


def _build_html(report: ReportOutput, *, company: str, scan_date: str) -> str:
    v = report.verdict
    fg, bg_badge, border_badge = _verdict_badge_style(v)
    thin = (report.chunk_count or 0) < 5

    parts: list[str] = []
    foot: list[str] = []
    n = 1

    pq = [p for p in (getattr(report, "probe_questions", None) or []) if (p or "").strip()][:3]
    exec_sec = report.sections["executive_summary"]
    exec_cites = list(exec_sec.citations)
    display_cites = _merge_citation_display_order(exec_cites, pq)
    for cid in display_cites:
        foot.append(
            f'<p id="fn{n}" class="fn"><span class="fn-num">{n}.</span> chunk_id: {_escape(cid)}</p>'
        )
        n += 1
    exec_fn_start = 1
    exec_fn_count = len(display_cites)

    exec_raw = (exec_sec.text or "").strip()
    exec_body_norm = _normalize_chunk_id_refs(exec_raw, display_cites)
    exec_body_html = (
        _html_body_with_inline_cites(exec_body_norm, exec_fn_start, exec_fn_count) if exec_raw else ""
    )
    pq_norm = [_normalize_chunk_id_refs(p, display_cites) for p in pq]
    probes_ul = "".join(
        f"<li>{_html_body_with_inline_cites(pn, exec_fn_start, exec_fn_count)}</li>" for pn in pq_norm
    )
    probes_inner = (
        f'<div class="probes-inner">'
        f'<h3>Before the call, probe</h3>'
        f"<ul>{probes_ul}</ul>"
        f"</div>"
        if pq
        else ""
    )
    if exec_raw or pq:
        parts.append(
            f'<section class="lane executive-lane">'
            f'<h2>Executive readout</h2>'
            f'<p class="status">{_escape(exec_sec.status)}</p>'
            f'<p class="body">{exec_body_html}</p>'
            f"{probes_inner}"
            f"</section>"
        )

    other_keys = (
        "legal_regulatory",
        "engineering_health",
        "hiring_trends",
        "funding_news",
    )
    for key in other_keys:
        sec = report.sections[key]
        if not (sec.text or "").strip():
            continue
        cites = list(sec.citations)
        start_fn = n
        for cid in cites:
            foot.append(
                f'<p id="fn{n}" class="fn"><span class="fn-num">{n}.</span> chunk_id: {_escape(cid)}</p>'
            )
            n += 1
        body_norm = _normalize_chunk_id_refs(sec.text or "", cites)
        body_html = _html_body_with_inline_cites(body_norm, start_fn, len(cites))
        parts.append(
            f'<section class="lane">'
            f'<h2>{_escape(key.replace("_", " "))}</h2>'
            f'<p class="status">{_escape(sec.status)}</p>'
            f'<p class="body">{body_html}</p></section>'
        )

    unknowns = "".join(f"<li>{_escape(u)}</li>" for u in report.known_unknowns)
    footer_block = "\n".join(foot)

    prelim_block = ""
    if thin:
        prelim_block = (
            f'<div class="notice">'
            f'<strong>Limited index</strong> — fewer than 5 sources indexed. '
            f"Treat as preliminary; verify claims against primary sources."
            f"</div>"
        )

    meta_line = (
        f"{report.chunk_count or 0} indexed source(s) · "
        f"{report.lane_coverage or 0} of 4 lanes returned usable data"
    )
    triage_line = _escape(_risk_triage_line(getattr(report, "risk_triage", "unknown")))

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&amp;family=DM+Sans:wght@400;500&amp;family=Instrument+Sans:wght@500;600&amp;display=swap" />
<style>
@page {{
  size: A4;
  margin: 16mm 18mm 20mm 18mm;
  @bottom-center {{
    content: counter(page) " / " counter(pages);
    font-size: 9px;
    color: {C_TEXT_SUBTLE};
    font-family: "DM Sans", Helvetica, Arial, sans-serif;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: "DM Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 11px;
  line-height: 1.55;
  color: {C_TEXT};
  background: {C_BG};
  margin: 0;
  padding: 0;
}}
header {{
  background: {C_SURFACE};
  border: 1px solid {C_BORDER};
  border-radius: 14px;
  padding: 20px 22px;
  margin-bottom: 18px;
  box-shadow: 0 1px 3px rgb(15 23 42 / 0.06);
}}
.brand {{
  font-family: "Instrument Sans", "DM Sans", sans-serif;
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.02em;
  color: {C_ACCENT};
  margin-bottom: 6px;
}}
h1 {{
  font-family: "Instrument Sans", "DM Sans", sans-serif;
  font-weight: 600;
  font-size: 20px;
  margin: 0 0 12px 0;
  color: {C_TEXT};
  letter-spacing: -0.02em;
}}
.verdict {{
  display: inline-block;
  padding: 6px 12px;
  background: {bg_badge};
  color: {fg};
  border: 1px solid {border_badge};
  font-weight: 600;
  font-family: "DM Mono", ui-monospace, monospace;
  font-size: 10px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border-radius: 6px;
}}
.meta {{
  font-size: 10px;
  color: {C_TEXT_MUTED};
  margin-top: 12px;
  line-height: 1.5;
}}
.notice {{
  margin-top: 14px;
  padding: 10px 12px;
  background: {C_NOTICE_BG};
  border: 1px solid {C_NOTICE_BORDER};
  border-radius: 10px;
  color: {C_NOTICE_TEXT};
  font-size: 10px;
}}
.notice strong {{ font-weight: 600; }}
.probes {{
  background: {C_SURFACE};
  border: 1px solid {C_BORDER};
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 14px;
  page-break-inside: avoid;
  box-shadow: 0 1px 3px rgb(15 23 42 / 0.06);
}}
.probes h3 {{
  font-family: "Instrument Sans", "DM Sans", sans-serif;
  font-weight: 600;
  font-size: 12px;
  color: {C_ACCENT};
  margin: 0 0 10px 0;
}}
.probes ul {{ margin: 0; padding-left: 18px; color: {C_TEXT}; }}
.probes li {{ margin-bottom: 6px; }}
.probes-inner {{
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid {C_BORDER};
}}
.probes-inner h3 {{
  font-family: "Instrument Sans", "DM Sans", sans-serif;
  font-weight: 600;
  font-size: 11px;
  color: {C_ACCENT};
  margin: 0 0 8px 0;
}}
.probes-inner ul {{ margin: 0; padding-left: 18px; color: {C_TEXT}; }}
.probes-inner li {{ margin-bottom: 6px; }}
.cite-ref a {{ color: inherit; text-decoration: none; }}
.lane {{
  background: {C_SURFACE};
  border: 1px solid {C_BORDER};
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 14px;
  page-break-inside: avoid;
  box-shadow: 0 1px 3px rgb(15 23 42 / 0.06);
}}
.lane h2 {{
  font-family: "Instrument Sans", "DM Sans", sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: {C_ACCENT};
  text-transform: capitalize;
  margin: 0 0 4px 0;
}}
.status {{
  font-size: 10px;
  color: {C_TEXT_MUTED};
  margin: 0 0 10px 0;
}}
.body {{ margin: 0; white-space: pre-wrap; }}
.cite-ref {{
  font-family: "DM Mono", ui-monospace, monospace;
  font-size: 9px;
  color: {C_ACCENT};
  font-weight: 500;
}}
.known-wrap {{
  background: {C_SURFACE};
  border: 1px solid {C_NOTICE_BORDER};
  border-radius: 14px;
  padding: 16px 18px;
  margin: 18px 0;
  page-break-inside: avoid;
}}
.known-wrap h3 {{
  font-family: "Instrument Sans", "DM Sans", sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: {C_NOTICE_TEXT};
  margin: 0 0 10px 0;
}}
.known-wrap ul {{ margin: 0; padding-left: 18px; color: {C_TEXT_MUTED}; }}
.known-wrap li {{ margin-bottom: 4px; }}
.sources-title {{
  font-family: "Instrument Sans", "DM Sans", sans-serif;
  font-size: 11px;
  font-weight: 600;
  color: {C_TEXT_MUTED};
  margin: 20px 0 8px 0;
}}
.fn {{
  font-size: 9px;
  color: {C_TEXT_MUTED};
  margin: 4px 0;
  font-family: "DM Mono", ui-monospace, monospace;
}}
.fn-num {{ color: {C_ACCENT}; font-weight: 600; margin-right: 4px; }}
.disclaimer {{
  font-size: 9px;
  color: {C_TEXT_SUBTLE};
  margin-top: 22px;
  padding-top: 14px;
  border-top: 1px solid {C_BORDER};
  line-height: 1.45;
}}
</style></head><body>
<header>
  <div class="brand">DealScannr</div>
  <h1>{_escape(company)}</h1>
  <p class="meta" style="margin-bottom:10px;font-weight:600">{triage_line}</p>
  <div class="verdict">{_escape(v)}</div>
  <p class="meta">Scan date: {_escape(scan_date)}<br/>{meta_line}</p>
  {prelim_block}
</header>
{"".join(parts)}
<div class="known-wrap">
  <h3>What we couldn&apos;t find</h3>
  <ul>{unknowns or "<li>None listed</li>"}</ul>
</div>
<p class="sources-title">Source notes</p>
{footer_block}
<p class="disclaimer">{_escape(report.disclaimer)}</p>
</body></html>"""


async def generate_report_pdf(
    report: ReportOutput,
    scan: dict[str, Any],
    entity: dict[str, Any] | None,
) -> bytes:
    company = str(
        scan.get("legal_name")
        or (entity.get("legal_name") if entity else "")
        or "Company",
    )
    created = scan.get("created_at")
    if isinstance(created, datetime):
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        else:
            created = created.astimezone(timezone.utc)
        scan_date = created.strftime("%Y-%m-%d %H:%M UTC")
    else:
        scan_date = str(created or "")
    html = _build_html(report, company=company, scan_date=scan_date)

    def _run() -> bytes:
        from weasyprint import HTML

        return HTML(string=html).write_pdf()

    return await asyncio.to_thread(_run)


def pdf_cache_valid(rep: dict[str, Any], content_hash: str) -> bool:
    cached = rep.get("pdf_cache")
    return (
        cached is not None
        and rep.get("content_hash") == content_hash
    )


def binary_pdf(cached: Any) -> bytes:
    if isinstance(cached, Binary):
        return bytes(cached)
    if isinstance(cached, (bytes, bytearray)):
        return bytes(cached)
    return b""


__all__ = [
    "generate_report_pdf",
    "pdf_cache_valid",
    "binary_pdf",
    "_report_content_hash",
]
