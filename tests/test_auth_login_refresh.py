from app.api.v1 import auth


def test_login_success(client, monkeypatch, override_db_dependency):
    async def fake_login_issue_tokens(db, username, password):
        assert username == "alice"
        assert password == "secret"
        return "access-token", "refresh-token"

    monkeypatch.setattr(auth, "login_issue_tokens", fake_login_issue_tokens)

    response = client.post(
        "/api/login",
        data={"username": "alice", "password": "secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "access-token"
    assert payload["token_type"] == "bearer"


def test_login_sets_refresh_cookie_flags(client, monkeypatch, override_db_dependency):
    async def fake_login_issue_tokens(db, username, password):
        return "access-token", "refresh-token"

    monkeypatch.setattr(auth, "login_issue_tokens", fake_login_issue_tokens)

    response = client.post(
        "/api/login",
        data={"username": "alice", "password": "secret"},
    )

    assert response.status_code == 200
    cookie = response.headers.get("set-cookie", "")
    assert "refresh=refresh-token" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_refresh_success(client, monkeypatch, override_db_dependency):
    async def fake_refresh_issue_tokens(db, token):
        assert token == "old-refresh"
        return "new-access", "new-refresh"

    monkeypatch.setattr(auth, "refresh_issue_tokens", fake_refresh_issue_tokens)
    client.cookies.set("refresh", "old-refresh")

    response = client.post("/api/refresh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "new-access"
    assert payload["token_type"] == "bearer"


def test_invalid_refresh_returns_401(client):
    response = client.post("/api/refresh")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "HTTP_ERROR"
    assert payload["error"]["message"] == "Didnt send refresh token"


def test_logout_clears_refresh_cookie(client, override_db_dependency):
    client.cookies.set("refresh", "some-token")

    response = client.post("/api/logout")

    assert response.status_code == 200
    cookie = response.headers.get("set-cookie", "")
    assert "refresh=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
