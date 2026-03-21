from __future__ import annotations

import json
import time


def _wait_report(client, scan_id: str, headers: dict, timeout: float = 8.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(f"/api/scans/{scan_id}/report", headers=headers)
        if last.status_code != 202:
            return last
        time.sleep(0.08)
    return last


def _full_scan(client, auth_headers, mock_embed, mock_groq, mock_connectors, allow_scan_rate_limit):
    r = client.post(
        "/api/entity/confirm",
        json={"legal_name": "PdfCo", "domain": "pdfco.test"},
        headers=auth_headers,
    )
    eid = r.json()["entity_id"]
    r = client.post(
        "/api/scans",
        json={"entity_id": eid, "legal_name": "PdfCo", "domain": "pdfco.test"},
        headers=auth_headers,
    )
    scan_id = r.json()["scan_id"]
    rep = _wait_report(client, scan_id, auth_headers)
    return scan_id, rep


def test_pdf_export_returns_pdf_bytes(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
    monkeypatch,
):
    async def fake_pdf(*_a, **_k):
        return b"%PDF-1.4 test-bytes"

    monkeypatch.setattr("modules.scans.router.generate_report_pdf", fake_pdf)
    scan_id, rep = _full_scan(client, auth_headers, mock_embed, mock_groq, mock_connectors, allow_scan_rate_limit)
    assert rep.status_code == 200
    r = client.get(f"/api/scans/{scan_id}/report/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content.startswith(b"%PDF")


def test_pdf_export_requires_auth(client):
    r = client.get("/api/scans/507f1f77bcf86cd799439011/report/pdf")
    assert r.status_code == 401


def test_pdf_export_only_scan_owner(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
    monkeypatch,
):
    async def fake_pdf(*_a, **_k):
        return b"%PDF-1.4 x"

    monkeypatch.setattr("modules.scans.router.generate_report_pdf", fake_pdf)
    scan_id, _ = _full_scan(client, auth_headers, mock_embed, mock_groq, mock_connectors, allow_scan_rate_limit)
    other = client.post(
        "/api/auth/register",
        json={"email": "other_pdf@dealscannr.test", "password": "password12345"},
    )
    otok = other.json()["token"]
    r = client.get(
        f"/api/scans/{scan_id}/report/pdf",
        headers={"Authorization": f"Bearer {otok}"},
    )
    assert r.status_code == 403


def test_share_creates_token(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    scan_id, rep = _full_scan(client, auth_headers, mock_embed, mock_groq, mock_connectors, allow_scan_rate_limit)
    assert rep.status_code == 200
    r = client.post(f"/api/scans/{scan_id}/share", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "token" in data and "share_url" in data
    assert "/share/" in data["share_url"]


def test_share_public_endpoint_no_auth(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    scan_id, _ = _full_scan(client, auth_headers, mock_embed, mock_groq, mock_connectors, allow_scan_rate_limit)
    r = client.post(f"/api/scans/{scan_id}/share", headers=auth_headers)
    token = r.json()["token"]
    pub = client.get(f"/api/share/{token}")
    assert pub.status_code == 200
    body = pub.json()
    assert "report" in body
    assert "entity_name" in body


def test_share_expired_token_returns_404(client, monkeypatch):
    async def none_payload(_db, _token):
        return None

    monkeypatch.setattr("modules.reports.share_links.fetch_shared_payload", none_payload)
    r = client.get("/api/share/deadbeefdeadbeefdeadbeefdeadbeef")
    assert r.status_code == 404
    assert r.json().get("error") == "share_expired"


def test_share_does_not_expose_user_id(
    client,
    auth_headers,
    mock_embed,
    mock_groq,
    mock_connectors,
    allow_scan_rate_limit,
):
    scan_id, _ = _full_scan(client, auth_headers, mock_embed, mock_groq, mock_connectors, allow_scan_rate_limit)
    token = client.post(f"/api/scans/{scan_id}/share", headers=auth_headers).json()["token"]
    body = client.get(f"/api/share/{token}").json()
    raw = json.dumps(body)
    assert "user_id" not in raw.lower()
    assert "email" not in body
