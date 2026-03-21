from __future__ import annotations

import os

import pytest


def _pro_user(db, pro: bool):
    u = db.users.find_one({"email": "pytest_user@dealscannr.test"})
    db.users.update_one({"_id": u["_id"]}, {"$set": {"plan_tier": "pro" if pro else "free"}})


def test_create_api_key_pro_only(client, auth_headers):
    from pymongo import MongoClient

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    _pro_user(db, False)
    try:
        r = client.post(
            "/api/keys",
            json={"name": "k1", "scopes": ["scan", "read"]},
            headers=auth_headers,
        )
        assert r.status_code == 403
    finally:
        _pro_user(db, False)


def test_full_key_returned_once_only(client, auth_headers):
    from pymongo import MongoClient

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    _pro_user(db, True)
    try:
        r = client.post(
            "/api/keys",
            json={"name": "k1", "scopes": ["scan", "read"]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["key"].startswith("ds_live_")
        assert "key" not in client.get("/api/keys", headers=auth_headers).json()["keys"][0]
        lst = client.get("/api/keys", headers=auth_headers).json()["keys"]
        assert lst[0]["prefix"] == body["prefix"]
    finally:
        db.api_keys.delete_many({"user_id": db.users.find_one({"email": "pytest_user@dealscannr.test"})["_id"]})
        _pro_user(db, False)


def test_api_key_auth_works_on_scan_endpoint(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    from pymongo import MongoClient

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    _pro_user(db, True)
    try:
        cr = client.post(
            "/api/keys",
            json={"name": "auto", "scopes": ["scan", "read"]},
            headers=auth_headers,
        )
        api_key = cr.json()["key"]
        e = client.post(
            "/api/entity/confirm",
            json={"legal_name": "KeyScanCo", "domain": "keyscanco.test"},
            headers=auth_headers,
        )
        eid = e.json()["entity_id"]
        headers = {"Authorization": f"Bearer {api_key}"}
        r = client.post(
            "/api/scans",
            json={
                "entity_id": eid,
                "legal_name": "KeyScanCo",
                "domain": "keyscanco.test",
            },
            headers=headers,
        )
        assert r.status_code == 200
    finally:
        db.api_keys.delete_many({"user_id": db.users.find_one({"email": "pytest_user@dealscannr.test"})["_id"]})
        _pro_user(db, False)


def test_deleted_key_rejected(client, auth_headers):
    from pymongo import MongoClient

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    _pro_user(db, True)
    try:
        cr = client.post(
            "/api/keys",
            json={"name": "tmp", "scopes": ["scan", "read"]},
            headers=auth_headers,
        )
        api_key = cr.json()["key"]
        prefix = cr.json()["prefix"]
        d = client.delete(f"/api/keys/{prefix}", headers=auth_headers)
        assert d.status_code == 200
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {api_key}"})
        assert me.status_code == 401
    finally:
        db.api_keys.delete_many({"user_id": db.users.find_one({"email": "pytest_user@dealscannr.test"})["_id"]})
        _pro_user(db, False)


def test_max_5_keys_per_user(client, auth_headers):
    from pymongo import MongoClient

    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    uid = db.users.find_one({"email": "pytest_user@dealscannr.test"})["_id"]
    _pro_user(db, True)
    db.api_keys.delete_many({"user_id": uid})
    try:
        for i in range(5):
            r = client.post(
                "/api/keys",
                json={"name": f"k{i}", "scopes": ["scan", "read"]},
                headers=auth_headers,
            )
            assert r.status_code == 200
        r6 = client.post(
            "/api/keys",
            json={"name": "overflow", "scopes": ["scan", "read"]},
            headers=auth_headers,
        )
        assert r6.status_code == 400
    finally:
        db.api_keys.delete_many({"user_id": uid})
        _pro_user(db, False)
