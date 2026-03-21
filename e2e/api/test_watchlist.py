from __future__ import annotations

import pytest
def _confirm_entity(client, headers: dict) -> str:
    r = client.post(
        "/api/entity/confirm",
        json={"legal_name": "WatchCo", "domain": "watchco.test"},
        headers=headers,
    )
    assert r.status_code == 200
    return r.json()["entity_id"]


def test_add_to_watchlist(client, auth_headers):
    eid = _confirm_entity(client, auth_headers)
    r = client.post(
        "/api/watchlist",
        json={"entity_id": eid, "notify_on": ["all"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["entity_id"] == eid
    assert body["notify_on"] == ["all"]


def test_patch_watchlist_notify_on(client, auth_headers):
    eid = _confirm_entity(client, auth_headers)
    client.post("/api/watchlist", json={"entity_id": eid}, headers=auth_headers)
    r = client.patch(
        f"/api/watchlist/{eid}",
        json={"notify_on": ["verdict_change"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["notify_on"] == ["verdict_change"]


def test_remove_from_watchlist(client, auth_headers):
    eid = _confirm_entity(client, auth_headers)
    client.post("/api/watchlist", json={"entity_id": eid}, headers=auth_headers)
    r = client.delete(f"/api/watchlist/{eid}", headers=auth_headers)
    assert r.status_code == 200
    lst = client.get("/api/watchlist", headers=auth_headers)
    assert lst.json()["entries"] == []


def test_watchlist_limit_by_plan(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "modules.credits.service.PLAN_WATCHLIST_LIMITS",
        {"free": 2, "pro": 50, "team": 100},
    )
    for i in range(2):
        r = client.post(
            "/api/entity/confirm",
            json={"legal_name": f"WL{i}", "domain": f"wl{i}.test"},
            headers=auth_headers,
        )
        eid = r.json()["entity_id"]
        a = client.post("/api/watchlist", json={"entity_id": eid}, headers=auth_headers)
        assert a.status_code == 200
    r = client.post(
        "/api/entity/confirm",
        json={"legal_name": "WLx", "domain": "wlx.test"},
        headers=auth_headers,
    )
    eid3 = r.json()["entity_id"]
    r3 = client.post("/api/watchlist", json={"entity_id": eid3}, headers=auth_headers)
    assert r3.status_code == 400
    assert r3.json().get("error") == "watchlist_limit"


def test_watchlist_job_skips_job_scans_for_credits():
    import inspect
    from pathlib import Path

    from modules.scans.pipeline import run_scan_pipeline

    sig = inspect.signature(run_scan_pipeline)
    assert "skip_credit_deduct" in sig.parameters
    job_src = Path(__file__).resolve().parents[2] / "packages" / "api" / "jobs" / "watchlist_job.py"
    assert "skip_credit_deduct=True" in job_src.read_text(encoding="utf-8")
