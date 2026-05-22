from app.api.v1 import auth
from app.core.settings import Settings


def test_secure_cookie_true_in_prod_config():
    prod_settings = Settings(_env_file=Settings.path_env_file)
    assert prod_settings.ENV.lower() == "prod"
    assert prod_settings.SECURE_COOKIE is True


def test_refresh_cookie_has_httponly_and_samesite(client, monkeypatch, override_db_dependency):
    async def fake_login_issue_tokens(db, username, password):
        return "access-token", "refresh-token"

    monkeypatch.setattr(auth, "login_issue_tokens", fake_login_issue_tokens)

    response = client.post(
        "/api/login",
        data={"username": "alice", "password": "secret"},
    )

    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header
    assert "SameSite=lax" in set_cookie_header
    assert "Secure" in set_cookie_header
