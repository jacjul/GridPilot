from app.api.v1 import health as health_api

from tests.route_contract_helpers import HealthyRedis


def test_health_routes_contract(client, monkeypatch, override_db_dependency):
    monkeypatch.setattr(health_api, "r", HealthyRedis())

    res_health = client.get("/api/healthz")
    assert res_health.status_code == 200

    res_ready = client.get("/api/readyz")
    assert res_ready.status_code == 200
