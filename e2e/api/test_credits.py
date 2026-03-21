from __future__ import annotations

import os
import time

from pymongo import MongoClient


def _wait_report(client, scan_id: str, headers: dict, timeout: float = 8.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(f"/api/scans/{scan_id}/report", headers=headers)
        if last.status_code != 202:
            return last
        time.sleep(0.08)
    return last


def test_credits_endpoint_returns_plan_info(client, auth_headers):
    r = client.get("/api/users/me/credits", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["remaining"] == 3
    assert data["plan"] == "free"
    assert data["monthly_limit"] == 3
    assert data["monthly_used"] == 0
    assert "resets_at" in data


def test_credit_ledger_has_entry_after_scan(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    eid = client.post(
        "/api/entity/confirm",
        json={"legal_name": "CredCo", "domain": "credco.test"},
        headers=auth_headers,
    ).json()["entity_id"]
    scan_id = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "CredCo", "domain": "credco.test"},
        headers=auth_headers,
    ).json()["scan_id"]
    _wait_report(client, scan_id, auth_headers)

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    u = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    uid = str(u["_id"])
    n = db.credit_ledger.count_documents({"user_id": uid, "scan_id": scan_id, "action": "deduct"})
    assert n >= 1


def test_credit_ledger_idempotent_no_double_deduct(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    """At most one deduct ledger row per scan_id after a successful chargeable scan."""
    eid = client.post(
        "/api/entity/confirm",
        json={"legal_name": "IdemCo", "domain": "idemco.test"},
        headers=auth_headers,
    ).json()["entity_id"]
    scan_id = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "IdemCo", "domain": "idemco.test"},
        headers=auth_headers,
    ).json()["scan_id"]
    _wait_report(client, scan_id, auth_headers)
    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    u = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    uid = str(u["_id"])
    n = db.credit_ledger.count_documents({"user_id": uid, "scan_id": scan_id, "action": "deduct"})
    assert n == 1


def test_no_credit_deduction_when_insufficient(
    client,
    auth_headers,
    mock_embed,
    mock_connectors_all_fail,
    mock_groq_insufficient,
    allow_scan_rate_limit,
):
    """INSUFFICIENT completion must leave monthly credits unchanged."""
    eid = client.post(
        "/api/entity/confirm",
        json={"legal_name": "ThinCo", "domain": "thinco.test"},
        headers=auth_headers,
    ).json()["entity_id"]
    scan_id = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "ThinCo", "domain": "thinco.test"},
        headers=auth_headers,
    ).json()["scan_id"]
    _wait_report(client, scan_id, auth_headers)
    me = client.get("/api/auth/me", headers=auth_headers)
    assert me.json()["credits"] == 3
