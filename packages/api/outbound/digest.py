"""Resend-powered digest and batch summary emails."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class DigestItem:
    entity_name: str
    domain: str
    verdict: str
    verdict_changed: bool
    previous_verdict: str | None
    notable_changes: list[str]
    report_url: str
    scan_date: datetime


def _verdict_color(v: str) -> str:
    m = {
        "MEET": "#22C55E",
        "PASS": "#EAB308",
        "FLAG": "#EF4444",
        "INSUFFICIENT": "#6B7280",
    }
    return m.get(v.upper(), "#9CA3AF")


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _digest_html(
    user_name: str,
    items: list[DigestItem],
    public_app_url: str,
) -> str:
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")
    rows = []
    for it in items:
        color = _verdict_color(it.verdict)
        bullets = "".join(f"<li>{_esc(x)}</li>" for x in (it.notable_changes or [])[:3])
        change = ""
        if it.verdict_changed and it.previous_verdict:
            change = (
                f'<p style="margin:8px 0;color:#EAB308">⚡ Verdict changed: '
                f"{_esc(it.previous_verdict)} → {_esc(it.verdict)}</p>"
            )
        rows.append(
            f"""
            <div style="border:1px solid #374151;border-radius:8px;padding:16px;margin-bottom:16px;background:#111">
              <h3 style="margin:0 0 4px;font-size:16px">{_esc(it.entity_name)}</h3>
              <p style="margin:0;color:#9CA3AF;font-size:13px">{_esc(it.domain or "—")}</p>
              <p style="margin:12px 0"><span style="color:{color};font-weight:bold;font-family:monospace">{_esc(it.verdict)}</span></p>
              {change}
              <ul style="margin:8px 0;padding-left:20px;color:#E5E7EB;font-size:14px">{bullets}</ul>
              <a href="{_esc(it.report_url)}" style="color:#D4A843">View full report →</a>
            </div>
            """
        )
    body = "\n".join(rows)
    settings_url = f"{public_app_url.rstrip('/')}/settings"
    return f"""<!DOCTYPE html>
<html><body style="background:#0A0A0A;color:#F0EDE8;font-family:system-ui,sans-serif;padding:24px">
  <p style="color:#D4A843;font-weight:600">DEALSCANNR</p>
  <p style="color:#6B7280;font-size:13px">Weekly digest · {when}</p>
  <p style="margin:16px 0">Hi {_esc(user_name or "there")},</p>
  {body}
  <p style="margin-top:24px;font-size:13px">
    <a href="{_esc(settings_url)}" style="color:#9CA3AF">Manage watchlist / settings</a>
  </p>
  <p style="margin-top:16px;font-size:11px;color:#6B7280">
    AI-generated snapshot from public sources — not investment advice.
  </p>
</body></html>"""


def _send_resend_sync(*, to: str, subject: str, html: str) -> bool:
    if not settings.resend_api_key:
        logger.warning("resend_skipped_no_api_key to=%s", to)
        return False
    try:
        import resend

        resend.api_key = settings.resend_api_key
        params: dict[str, Any] = {
            "from": settings.resend_from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.exception("resend_send_failed: %s", e)
        return False


async def send_watchlist_digest(
    user_email: str,
    user_name: str,
    digest_items: list[DigestItem],
) -> bool:
    if not digest_items:
        return False
    n = len(digest_items)
    subject = f"DealScannr Weekly: {n} companies updated"
    html = _digest_html(user_name, digest_items, settings.public_app_url)
    return await asyncio.to_thread(
        _send_resend_sync,
        to=user_email,
        subject=subject,
        html=html,
    )


def _batch_html(rows_html: str, public_app_url: str) -> str:
    settings_url = f"{public_app_url.rstrip('/')}/settings"
    return f"""<!DOCTYPE html>
<html><body style="background:#0A0A0A;color:#F0EDE8;font-family:system-ui,sans-serif;padding:24px">
  <p style="color:#D4A843;font-weight:600">DEALSCANNR</p>
  <h2 style="margin:16px 0">Batch scan complete</h2>
  <table style="width:100%;border-collapse:collapse;font-size:14px">
    <thead><tr style="text-align:left;border-bottom:1px solid #374151">
      <th style="padding:8px">Company</th><th style="padding:8px">Verdict</th><th style="padding:8px">Report</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <p style="margin-top:24px;font-size:13px"><a href="{_esc(settings_url)}" style="color:#9CA3AF">Settings</a></p>
</body></html>"""


async def send_batch_complete_email(
    user_email: str,
    rows: list[dict[str, Any]],
) -> bool:
    if not rows:
        return False
    parts = []
    for r in rows:
        parts.append(
            "<tr>"
            f'<td style="padding:8px;border-bottom:1px solid #1f2937">{_esc(str(r.get("company_name") or ""))}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #1f2937;color:{_verdict_color(str(r.get("verdict") or ""))}">'
            f'{_esc(str(r.get("verdict") or "—"))}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #1f2937"><a href="{_esc(str(r.get("report_url") or "#"))}" style="color:#D4A843">Open</a></td>'
            "</tr>"
        )
    html = _batch_html("\n".join(parts), settings.public_app_url)
    subject = f"Batch scan complete: {len(rows)} companies"
    return await asyncio.to_thread(
        _send_resend_sync,
        to=user_email,
        subject=subject,
        html=html,
    )
