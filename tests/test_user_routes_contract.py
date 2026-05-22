from app.api.v1 import user as user_api
from app.main import app
from app.services import auth_service

from tests.route_contract_helpers import auth_headers, override_current_user


def test_user_routes_contract(client, monkeypatch, override_db_dependency):
    async def fake_get_current_user(db, token):
        return {
            "id": 42,
            "name": "Test",
            "lastname": "User",
            "username": "tester",
            "email": "tester@example.com",
            "annual_consumption_kwh": 3500.0,
            "load_profile_type": "SLP",
        }

    async def fake_update_user_consumption_service(db, user_id, payload):
        return {
            "id": user_id,
            "name": "Test",
            "lastname": "User",
            "username": "tester",
            "email": "tester@example.com",
            "annual_consumption_kwh": float(payload.annual_consumption_kwh),
            "load_profile_type": payload.load_profile_type,
        }

    app.dependency_overrides[auth_service.get_current_user] = override_current_user
    monkeypatch.setattr(user_api, "get_current_user", fake_get_current_user)
    monkeypatch.setattr(user_api, "update_user_consumption_service", fake_update_user_consumption_service)

    res_me = client.get("/api/me", headers=auth_headers())
    assert res_me.status_code == 200

    res_patch = client.patch(
        "/api/me/consumption",
        headers=auth_headers(),
        json={"annual_consumption_kwh": 4200.0, "load_profile_type": "SLP"},
    )
    assert res_patch.status_code == 200
