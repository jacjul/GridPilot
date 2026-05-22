from app.api.v1 import auth as auth_api


def test_auth_routes_contract(client, monkeypatch, override_db_dependency):
    calls = {"register": False}

    async def fake_register_user(db, user):
        calls["register"] = True

    async def fake_login_issue_tokens(db, username, password):
        return "access-token", "refresh-token"

    async def fake_refresh_issue_tokens(db, token):
        return "new-access", "new-refresh"

    monkeypatch.setattr(auth_api, "register_user", fake_register_user)
    monkeypatch.setattr(auth_api, "login_issue_tokens", fake_login_issue_tokens)
    monkeypatch.setattr(auth_api, "refresh_issue_tokens", fake_refresh_issue_tokens)

    res_register = client.post(
        "/api/register",
        json={
            "name": "A",
            "lastname": "B",
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret",
        },
    )
    assert res_register.status_code == 201
    assert calls["register"] is True

    res_login = client.post("/api/login", data={"username": "alice", "password": "secret"})
    assert res_login.status_code == 200
    assert res_login.json()["token_type"] == "bearer"

    client.cookies.set("refresh", "old-refresh")
    res_refresh = client.post("/api/refresh")
    assert res_refresh.status_code == 200
    assert res_refresh.json()["token_type"] == "bearer"

    res_logout = client.post("/api/logout")
    assert res_logout.status_code == 200
