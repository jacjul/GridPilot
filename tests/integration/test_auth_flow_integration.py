from http.cookies import SimpleCookie


def _extract_refresh_cookie(set_cookie_header: str) -> str:
    cookie = SimpleCookie()
    cookie.load(set_cookie_header)
    return cookie["refresh"].value


def test_register_login_refresh_with_real_dependencies(client):
    register_response = client.post(
        "/api/register",
        json={
            "name": "Alice",
            "lastname": "Tester",
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/login",
        data={"username": "alice", "password": "secret"},
    )
    assert login_response.status_code == 200
    assert "refresh=" in login_response.headers.get("set-cookie", "")

    refresh_response = client.post("/api/refresh")
    assert refresh_response.status_code == 200
    payload = refresh_response.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"


def test_reusing_rotated_refresh_token_returns_401(client):
    client.post(
        "/api/register",
        json={
            "name": "Bob",
            "lastname": "Tester",
            "username": "bob",
            "email": "bob@example.com",
            "password": "secret",
        },
    )

    login_response = client.post(
        "/api/login",
        data={"username": "bob", "password": "secret"},
    )
    assert login_response.status_code == 200

    first_cookie = login_response.headers.get("set-cookie", "")
    first_refresh_token = _extract_refresh_cookie(first_cookie)

    client.cookies.clear()
    client.cookies.set("refresh", first_refresh_token)
    first_refresh_response = client.post("/api/refresh")
    assert first_refresh_response.status_code == 200

    client.cookies.clear()
    client.cookies.set("refresh", first_refresh_token)
    reuse_response = client.post("/api/refresh")
    assert reuse_response.status_code == 401
    payload = reuse_response.json()
    assert payload["error"]["code"] == "HTTP_ERROR"
    assert "reuse detected" in payload["error"]["message"].lower()


def test_readyz_with_real_dependencies_returns_200(client):
    response = client.get("/api/readyz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["redis"] == "ok"
