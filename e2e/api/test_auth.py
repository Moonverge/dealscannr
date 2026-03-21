from __future__ import annotations


def test_register_new_user(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "reg1@dealscannr.test", "password": "password12345"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data.get("user_id")


def test_register_duplicate_email_returns_409(client):
    body = {"email": "dup@dealscannr.test", "password": "password12345"}
    assert client.post("/api/auth/register", json=body).status_code == 200
    r2 = client.post("/api/auth/register", json=body)
    assert r2.status_code == 409
    assert r2.json().get("error") == "conflict"


def test_login_valid_credentials(client):
    client.post(
        "/api/auth/register",
        json={"email": "login@dealscannr.test", "password": "password12345"},
    )
    r = client.post(
        "/api/auth/login",
        json={"email": "login@dealscannr.test", "password": "password12345"},
    )
    assert r.status_code == 200
    assert r.json().get("token")


def test_login_wrong_password_returns_401(client):
    client.post(
        "/api/auth/register",
        json={"email": "badpw@dealscannr.test", "password": "password12345"},
    )
    r = client.post(
        "/api/auth/login",
        json={"email": "badpw@dealscannr.test", "password": "wrongpassword"},
    )
    assert r.status_code == 401
    assert r.json().get("error") == "unauthorized"


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_returns_user_and_credits(client, auth_headers):
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("credits") == 3
    assert data.get("plan") == "free"
    assert data["user"].get("email") == "pytest_user@dealscannr.test"
