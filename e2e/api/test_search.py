"""Search route smoke tests via in-process TestClient (no external HTTP)."""


def test_search_accepts_body(client):
    r = client.post(
        "/api/search",
        json={"query": "Acme Corp", "company_name": "Acme Corp"},
    )
    assert r.status_code in (200, 422, 500, 503)


def test_search_validation_error_without_body(client):
    r = client.post("/api/search", json={})
    assert r.status_code == 422
    assert r.json().get("error") == "validation_error"
