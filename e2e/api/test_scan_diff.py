"""Previous-scan helper and report diff endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from rag.schema.llm_report import REPORT_SECTION_KEYS, ReportOutput, ReportSection


def _confirm_entity(client, headers: dict) -> str:
    r = client.post(
        "/api/entity/confirm",
        json={"legal_name": "DiffCo", "domain": "diffco.test"},
        headers=headers,
    )
    assert r.status_code == 200
    return r.json()["entity_id"]


def _minimal_report(verdict: str, exec_text: str) -> dict:
    sections = {
        k: ReportSection(text="x" if k != "executive_summary" else exec_text, citations=[], status="complete")
        for k in REPORT_SECTION_KEYS
    }
    ro = ReportOutput(
        verdict=verdict,  # type: ignore[arg-type]  # MEET | PASS
        confidence_score=0.8,
        lane_coverage=4,
        chunk_count=5,
        risk_triage="watch",
        sections=sections,
        known_unknowns=[],
        disclaimer="d",
    )
    return ro.model_dump()


@pytest.fixture
def diff_scan_pair(client, auth_headers, monkeypatch):
    """Two completed scans same entity, with chunks, no pipeline."""
    from pymongo import MongoClient

    def _noop_complete(self, system: str, user: str, models=None):
        return "- Notable test bullet.\n- Second change.", {}

    monkeypatch.setattr("modules.scans.diff_service.RAGEngine._complete", _noop_complete)

    eid = _confirm_entity(client, auth_headers)
    import os

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    user = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    assert user
    uid = user["_id"]
    now = datetime.now(timezone.utc)

    oid_old = ObjectId()
    oid_new = ObjectId()
    db.scans.insert_one(
        {
            "_id": oid_old,
            "user_id": uid,
            "entity_id": eid,
            "legal_name": "DiffCo",
            "domain": "diffco.test",
            "status": "complete",
            "created_at": now,
            "credits_used": 1,
            "lane_coverage": 4,
        }
    )
    db.scans.insert_one(
        {
            "_id": oid_new,
            "user_id": uid,
            "entity_id": eid,
            "legal_name": "DiffCo",
            "domain": "diffco.test",
            "status": "complete",
            "created_at": now + timedelta(seconds=5),
            "credits_used": 1,
            "lane_coverage": 4,
        }
    )
    sid_old = str(oid_old)
    sid_new = str(oid_new)

    db.reports.insert_one(
        {
            "scan_id": sid_old,
            "entity_id": eid,
            "created_at": now,
            **_minimal_report("PASS", "Old executive summary text."),
        }
    )
    db.reports.insert_one(
        {
            "scan_id": sid_new,
            "entity_id": eid,
            "created_at": now,
            **_minimal_report("MEET", "New executive summary with more detail."),
        }
    )

    def _chunk(scan_id: str, conn: str, url: str):
        return {
            "_id": str(ObjectId()),
            "scan_id": scan_id,
            "entity_id": eid,
            "connector_id": conn,
            "source_url": url,
            "retrieved_at": now,
            "raw_text": "t",
            "normalized_text": "t",
            "embedding_model": "none",
            "embedding_dim": 0,
        }

    db.chunks.insert_one(_chunk(sid_old, "github_connector", "https://gh.example/old"))
    db.chunks.insert_one(_chunk(sid_new, "github_connector", "https://gh.example/old"))
    db.chunks.insert_one(_chunk(sid_new, "github_connector", "https://gh.example/new"))

    return sid_old, sid_new


def test_previous_scan_returns_older_id(client, auth_headers, diff_scan_pair):
    sid_old, sid_new = diff_scan_pair
    r = client.get(f"/api/scans/{sid_new}/previous-scan", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["previous_scan_id"] == sid_old


def test_diff_requires_same_entity_and_order(client, auth_headers, diff_scan_pair):
    sid_old, sid_new = diff_scan_pair
    r = client.get(
        f"/api/scans/{sid_new}/diff",
        params={"compare_to": sid_old},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["new_scan_id"] == sid_new
    assert body["previous_scan_id"] == sid_old
    assert body["verdict_changed"] is True
    assert body["verdict_before"] == "PASS"
    assert body["verdict_after"] == "MEET"
    assert body["changes"]["engineering"]["new_chunks"] == 1
    assert len(body["notable_changes"]) >= 1

    r2 = client.get(
        f"/api/scans/{sid_old}/diff",
        params={"compare_to": sid_new},
        headers=auth_headers,
    )
    assert r2.status_code == 400
