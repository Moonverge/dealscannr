from __future__ import annotations

import time

import pytest
from rag.schema.llm_report import ReportOutput


def _wait_report(client, scan_id: str, headers: dict, timeout: float = 8.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(f"/api/scans/{scan_id}/report", headers=headers)
        if last.status_code != 202:
            return last
        time.sleep(0.08)
    return last


def _confirm_entity(client, headers: dict) -> str:
    r = client.post(
        "/api/entity/confirm",
        json={"legal_name": "ScanCo", "domain": "scanco.test"},
        headers=headers,
    )
    assert r.status_code == 200
    return r.json()["entity_id"]


def test_create_scan_requires_auth(client):
    r = client.post("/api/scans", json={"entity_id": "x", "legal_name": "y"})
    assert r.status_code == 401


def test_create_scan_deducts_credits_on_meet_verdict(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    scan_id = r.json()["scan_id"]
    rep = _wait_report(client, scan_id, auth_headers)
    assert rep.status_code == 200
    body = rep.json()
    assert body.get("verdict") == "MEET"
    me = client.get("/api/auth/me", headers=auth_headers)
    assert me.json()["credits"] == 2


def test_create_scan_does_not_deduct_on_insufficient(
    client,
    auth_headers,
    mock_embed,
    mock_connectors_all_fail,
    mock_groq_insufficient,
    allow_scan_rate_limit,
):
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    scan_id = r.json()["scan_id"]
    rep = _wait_report(client, scan_id, auth_headers)
    assert rep.status_code == 200
    assert rep.json().get("verdict") == "INSUFFICIENT"
    me = client.get("/api/auth/me", headers=auth_headers)
    assert me.json()["credits"] == 3


def test_create_scan_returns_402_if_no_credits(client, auth_headers, allow_scan_rate_limit):
    import os
    from datetime import datetime, timezone

    from pymongo import MongoClient

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    u = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    now = datetime.now(timezone.utc)
    period = f"{now.year}-{now.month:02d}"
    db.users.update_one(
        {"_id": u["_id"]},
        {"$set": {"scan_credits": 0, "credits_period": period}},
    )
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    assert r.status_code == 402
    assert r.json().get("error") == "credits_exhausted"


def test_create_scan_returns_429_if_rate_limited(client, auth_headers, monkeypatch):
    async def block(_uid: str) -> bool:
        return False

    monkeypatch.setattr("modules.scans.router.check_scan_rate_limit", block)
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    assert r.status_code == 429
    assert r.json().get("error") == "rate_limited"


def test_scan_status_returns_lane_breakdown(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    scan_id = r.json()["scan_id"]
    st = client.get(f"/api/scans/{scan_id}/status", headers=auth_headers)
    assert st.status_code == 200
    lanes = st.json().get("lanes") or {}
    assert "litigation" in lanes
    assert "engineering" in lanes


def test_scan_report_validates_as_report_output(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    scan_id = r.json()["scan_id"]
    rep = _wait_report(client, scan_id, auth_headers)
    body = rep.json()
    core = {
        k: body[k]
        for k in (
            "verdict",
            "confidence_score",
            "lane_coverage",
            "chunk_count",
            "risk_triage",
            "probe_questions",
            "sections",
            "known_unknowns",
            "disclaimer",
        )
    }
    ReportOutput.model_validate(core)


def test_scan_report_has_no_hallucinated_citations(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    scan_id = r.json()["scan_id"]
    rep = _wait_report(client, scan_id, auth_headers)
    import os

    from pymongo import MongoClient

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    doc = db.reports.find_one({"scan_id": scan_id})
    assert int(doc.get("hallucinated_citations_count") or 0) == 0


def test_scan_report_returns_202_while_running(client, auth_headers, monkeypatch):
    """Background job never started → scan stays running → report returns 202."""

    def drop_task(coro):
        if hasattr(coro, "close"):
            coro.close()
        from unittest.mock import MagicMock

        return MagicMock()

    monkeypatch.setattr("modules.scans.router.asyncio.create_task", drop_task)
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    scan_id = r.json()["scan_id"]
    rep = client.get(f"/api/scans/{scan_id}/report", headers=auth_headers)
    assert rep.status_code == 202
    assert rep.json().get("error") == "report_processing"


def test_scan_report_returns_insufficient_on_all_connectors_failed(
    client,
    auth_headers,
    mock_embed,
    mock_connectors_all_fail,
    mock_groq_insufficient,
    allow_scan_rate_limit,
):
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ScanCo", "domain": "scanco.test"},
        headers=auth_headers,
    )
    scan_id = r.json()["scan_id"]
    rep = _wait_report(client, scan_id, auth_headers)
    assert rep.json().get("verdict") == "INSUFFICIENT"

