from __future__ import annotations

import os
from datetime import datetime, timezone

from pymongo import MongoClient


def _seed_entity(doc: dict) -> None:
    db = MongoClient(os.environ["DATABASE_URL"]).get_default_database()
    db.entities.insert_one(doc)


def test_resolve_by_domain_exact_match(client, auth_headers, clean_db):
    _seed_entity(
        {
            "legal_name": "ExactCo LLC",
            "domain": "exactco.com",
            "aliases": [],
            "confidence": 0.9,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    r = client.post(
        "/api/entity/resolve",
        json={"name": "Anything", "domain_hint": "exactco.com"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["confidence"] >= 0.9
    assert len(data["candidates"]) >= 1
    assert data["candidates"][0]["domain"] == "exactco.com"


def test_resolve_by_name_fuzzy_match(client, auth_headers, clean_db):
    _seed_entity(
        {
            "legal_name": "Stripe Inc",
            "domain": "stripe.com",
            "aliases": [],
            "confidence": 0.9,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    r = client.post(
        "/api/entity/resolve",
        json={"name": "Stripe Inc", "domain_hint": ""},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["confidence"] >= 0.85
    assert data["candidates"][0]["legal_name"] == "Stripe Inc"


def test_resolve_explicit_domain_skips_fuzzy_wrong_company(client, auth_headers, clean_db):
    """User types exact domain (e.g. kooya.ph) — never substitute a fuzzy DB hit with a different domain."""
    _seed_entity(
        {
            "legal_name": "Kooyal",
            "domain": "kooyal.com",
            "aliases": [],
            "confidence": 0.9,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    r = client.post(
        "/api/entity/resolve",
        json={"name": "kooya.ph", "domain_hint": "kooya.ph"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["domain"] == "kooya.ph"
    assert data["candidates"][0].get("source") == "explicit_domain"


def test_resolve_domain_hint_blocks_fuzzy_early_return_when_domains_differ(client, auth_headers, clean_db):
    """Fuzzy name match must not win when domain_hint points at a different intended domain."""
    _seed_entity(
        {
            "legal_name": "Kooyal",
            "domain": "kooyal.com",
            "aliases": [],
            "confidence": 0.9,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    r = client.post(
        "/api/entity/resolve",
        json={"name": "Kooya", "domain_hint": "kooya.ph"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["candidates"]
    assert data["candidates"][0]["domain"] == "kooya.ph"


def test_resolve_low_confidence_returns_candidates(client, auth_headers, clean_db):
    r = client.post(
        "/api/entity/resolve",
        json={"name": "Totally Unknown Startup XYZ", "domain_hint": ""},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "candidates" in data
    assert data["confidence"] < 0.85


def test_confirm_entity_creates_or_updates(client, auth_headers):
    r = client.post(
        "/api/entity/confirm",
        json={"legal_name": "NewCo", "domain": "newco.io"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("entity_id")
    assert data["legal_name"] == "NewCo"
    assert data["domain"] == "newco.io"
