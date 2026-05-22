from app.api.v1 import health
from app.main import app
from app.db.database import get_async_db


class HealthyDBSession:
    async def execute(self, *_args, **_kwargs):
        return 1


class UnhealthyDBSession:
    async def execute(self, *_args, **_kwargs):
        raise RuntimeError("database down")


class HealthyRedis:
    async def ping(self):
        return True


class UnhealthyRedis:
    async def ping(self):
        raise RuntimeError("redis down")


async def _override_healthy_db():
    yield HealthyDBSession()


async def _override_unhealthy_db():
    yield UnhealthyDBSession()


def test_healthz_returns_200(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_sets_request_id_header(client):
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_readyz_returns_200_when_dependencies_up(client, monkeypatch):
    monkeypatch.setattr(health, "r", HealthyRedis())
    app.dependency_overrides[get_async_db] = _override_healthy_db

    response = client.get("/api/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["redis"] == "ok"


def test_readyz_returns_503_when_db_down(client, monkeypatch):
    monkeypatch.setattr(health, "r", HealthyRedis())
    app.dependency_overrides[get_async_db] = _override_unhealthy_db

    response = client.get("/api/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["database"] == "down"
    assert "database" in payload["errors"]


def test_readyz_returns_503_when_redis_down(client, monkeypatch):
    monkeypatch.setattr(health, "r", UnhealthyRedis())
    app.dependency_overrides[get_async_db] = _override_healthy_db

    response = client.get("/api/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["redis"] == "down"
    assert "redis" in payload["errors"]
