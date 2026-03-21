"""Health endpoint: always 200 JSON; dependency failures are ok/error fields, not 500."""

from __future__ import annotations


def test_health_returns_all_services(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("api") == "ok"
    for key in ("mongo", "redis", "qdrant"):
        assert data.get(key) in ("ok", "error")


def test_health_qdrant_unreachable_returns_error_not_500(client, monkeypatch):
    import main

    async def bad_qdrant() -> str:
        return "error"

    monkeypatch.setattr(main, "_qdrant_status", bad_qdrant)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("qdrant") == "error"
    assert data.get("api") == "ok"
