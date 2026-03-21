from __future__ import annotations

import io

import pytest


def _csv_bytes(rows: list[tuple[str, str]]) -> bytes:
    lines = ["company_name,domain"] + [f"{a},{b}" for a, b in rows]
    return ("\n".join(lines)).encode("utf-8")


@pytest.fixture
def batch_sync(monkeypatch):
    monkeypatch.setenv("TEST_BATCH_SYNC", "1")


@pytest.fixture
def stub_batch_process(monkeypatch):
    async def finish(oid):
        from db.mongo import get_database

        db = get_database()
        job = await db.batch_jobs.find_one({"_id": oid})
        if not job:
            return
        rows = list(job.get("rows") or [])
        for i, row in enumerate(rows):
            rows[i] = {
                **row,
                "status": "complete",
                "scan_id": f"fake{i}",
                "verdict": "MEET",
                "entity_id": "e",
            }
        from datetime import datetime, timezone

        await db.batch_jobs.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "complete",
                    "completed": len(rows),
                    "failed": 0,
                    "rows": rows,
                    "completed_at": datetime.now(timezone.utc),
                }
            },
        )

    monkeypatch.setattr("modules.batch.router._process_batch_job", finish)


def test_batch_invalid_csv(client, auth_headers, batch_sync, stub_batch_process, monkeypatch):
    import os
    from datetime import datetime, timezone

    from pymongo import MongoClient

    monkeypatch.setattr(
        "modules.credits.service.PLAN_BATCH_MAX_ROWS",
        {"free": 0, "pro": 20, "team": 50},
    )
    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    u = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    db.users.update_one(
        {"_id": u["_id"]},
        {"$set": {"plan_tier": "pro", "scan_credits": 10, "credits_period": "2099-01"}},
    )
    try:
        b = b"not,a,csv\n1,2,3"
        r = client.post(
            "/api/batch",
            files={"file": ("co.csv", io.BytesIO(b), "text/csv")},
            headers=auth_headers,
        )
        assert r.status_code == 400
    finally:
        db.users.update_one(
            {"_id": u["_id"]},
            {
                "$set": {
                    "plan_tier": "free",
                    "scan_credits": 3,
                    "credits_period": f"{datetime.now(timezone.utc).year}-{datetime.now(timezone.utc).month:02d}",
                }
            },
        )


def test_batch_rejects_free_plan(client, auth_headers, batch_sync, stub_batch_process):
    b = _csv_bytes([("Acme", "acme.test")])
    r = client.post(
        "/api/batch",
        files={"file": ("co.csv", io.BytesIO(b), "text/csv")},
        headers=auth_headers,
    )
    assert r.status_code == 403
    assert r.json().get("error") == "plan_required"


def test_batch_rejects_if_insufficient_credits(client, auth_headers, batch_sync, stub_batch_process, monkeypatch):
    import os
    from datetime import datetime, timezone

    from pymongo import MongoClient

    monkeypatch.setattr(
        "modules.credits.service.PLAN_BATCH_MAX_ROWS",
        {"free": 0, "pro": 5, "team": 50},
    )
    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    u = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    now = datetime.now(timezone.utc)
    period = f"{now.year}-{now.month:02d}"
    db.users.update_one(
        {"_id": u["_id"]},
        {"$set": {"plan_tier": "pro", "scan_credits": 1, "credits_period": period}},
    )
    try:
        b = _csv_bytes([("A", "a.test"), ("B", "b.test")])
        r = client.post(
            "/api/batch",
            files={"file": ("co.csv", io.BytesIO(b), "text/csv")},
            headers=auth_headers,
        )
        assert r.status_code == 402
    finally:
        db.users.update_one(
            {"_id": u["_id"]},
            {
                "$set": {
                    "plan_tier": "free",
                    "scan_credits": 3,
                    "credits_period": f"{datetime.now(timezone.utc).year}-{datetime.now(timezone.utc).month:02d}",
                }
            },
        )


def test_batch_upload_csv(client, auth_headers, batch_sync, stub_batch_process, monkeypatch):
    import os
    from datetime import datetime, timezone

    from pymongo import MongoClient

    monkeypatch.setattr(
        "modules.credits.service.PLAN_BATCH_MAX_ROWS",
        {"free": 0, "pro": 20, "team": 50},
    )
    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    u = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    db.users.update_one(
        {"_id": u["_id"]},
        {"$set": {"plan_tier": "pro", "scan_credits": 10, "credits_period": "2099-01"}},
    )
    try:
        b = _csv_bytes([("BatchCo", "batchco.test")])
        r = client.post(
            "/api/batch",
            files={"file": ("co.csv", io.BytesIO(b), "text/csv")},
            headers=auth_headers,
        )
        assert r.status_code == 200
        bid = r.json()["batch_id"]
        st = client.get(f"/api/batch/{bid}", headers=auth_headers)
        assert st.status_code == 200
        body = st.json()
        assert body["status"] == "complete"
        assert body["results"][0]["status"] == "complete"
    finally:
        db.users.update_one(
            {"_id": u["_id"]},
            {
                "$set": {
                    "plan_tier": "free",
                    "scan_credits": 3,
                    "credits_period": f"{datetime.now(timezone.utc).year}-{datetime.now(timezone.utc).month:02d}",
                }
            },
        )


def test_batch_status_polling(client, auth_headers, batch_sync, stub_batch_process, monkeypatch):
    import os
    from datetime import datetime, timezone

    from pymongo import MongoClient

    monkeypatch.setattr(
        "modules.credits.service.PLAN_BATCH_MAX_ROWS",
        {"free": 0, "pro": 20, "team": 50},
    )
    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    u = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    db.users.update_one(
        {"_id": u["_id"]},
        {"$set": {"plan_tier": "team", "scan_credits": 10, "credits_period": "2099-01"}},
    )
    try:
        b = _csv_bytes([("X", "x.test")])
        r = client.post(
            "/api/batch",
            files={"file": ("co.csv", io.BytesIO(b), "text/csv")},
            headers=auth_headers,
        )
        bid = r.json()["batch_id"]
        st = client.get(f"/api/batch/{bid}", headers=auth_headers)
        assert st.json()["batch_id"] == bid
        assert "results" in st.json()
    finally:
        db.users.update_one(
            {"_id": u["_id"]},
            {
                "$set": {
                    "plan_tier": "free",
                    "scan_credits": 3,
                    "credits_period": f"{datetime.now(timezone.utc).year}-{datetime.now(timezone.utc).month:02d}",
                }
            },
        )
