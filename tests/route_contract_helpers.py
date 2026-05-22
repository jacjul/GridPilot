from types import SimpleNamespace

from app.api.v1 import battery as battery_api
from app.api.v1 import electric_vehicle as ev_api
from app.api.v1 import electricity as electricity_api
from app.api.v1 import optimization as optimization_api
from app.api.v1 import photovoltaik as pv_api
from app.main import app
from app.services import auth_service


class HealthyRedis:
    async def ping(self):
        return True


class FakeBESSService:
    async def create_bess(self, formdata, user, db):
        return {"id": 1, "owner_id": user.id, "kwh": formdata.kwh}

    async def update_bess(self, bess_id, formdata, user, db):
        return {"id": bess_id, "updated": True}

    async def delete_bess(self, bess_id, user, db):
        return {"id": bess_id, "deleted": True}

    async def get_bess(self, bess_id, user, db):
        if bess_id is None:
            return [{"id": 1}, {"id": 2}]
        return {"id": bess_id}


class FakeEVService:
    async def list_user_evs(self, user, db):
        return [{"id": 1, "ev_name": "e1"}]

    async def get_single_ev(self, ev_id, user, db):
        return {"id": ev_id, "ev_name": "e1"}

    async def create_new_EV(self, formdata, user, db):
        return {"id": 1, "ev_name": formdata.ev_name}

    async def update_ev(self, ev_id, formdata, user, db):
        return {"id": ev_id, "updated": True}

    async def delete_ev(self, ev_id, user, db):
        return {"id": ev_id, "deleted": True}

    async def create_new_blocker(self, formdata, user, db):
        return {"id": 10, "ev_id": formdata.ev_id}

    async def list_downtime_rules(self, ev_id, user, db):
        return [
            {
                "id": 1,
                "ev_id": ev_id,
                "weekdays_mask": 31,
                "start_time": "08:00:00",
                "end_time": "10:00:00",
                "valid_from": None,
                "valid_to": None,
                "soc_target_start_pct": None,
                "soc_target_end_pct": None,
                "tz_name": "Europe/Berlin",
            }
        ]

    async def update_new_blocker(self, ev_id, rule_id, formdata, user, db):
        return {"id": rule_id, "ev_id": ev_id, "updated": True}

    async def delete_new_blocker(self, ev_id, rule_id, user, db):
        return {"id": rule_id, "ev_id": ev_id, "deleted": True}


class FakeElectricityService:
    async def create_electricity_tarif(self, formdata, user, db):
        return {"id": 1, "name": formdata.name or "fixed"}

    async def get_tariffs(self, user, db, tariff_id=None):
        payload = {
            "id": tariff_id or 1,
            "owner_id": user.id,
            "name": "main",
            "price_typ": "fixed",
            "fixed_price": 0.3,
            "market_zone": "DE-LU",
            "is_active": True,
        }
        if tariff_id is None:
            return [payload]
        return payload

    async def update_tariff(self, tariff_id, formdata, user, db):
        return {"id": tariff_id, "updated": True}

    async def delete_tariff(self, tariff_id, user, db):
        return {"id": tariff_id, "deleted": True}


class FakePVService:
    async def create_new_PV(self, formData, user, db):
        return {"id": 1, "owner_id": user.id}

    async def get_PV_data(self, user, db):
        return [
            {
                "id": 1,
                "latitude": 52.52,
                "longitude": 13.405,
                "declination": 30.0,
                "azimuth": 180.0,
                "kw_peak": 9.5,
                "einspeiseverguetung": 0.08,
            }
        ]

    async def get_single_PV(self, pv_id, user, db):
        return {
            "id": pv_id,
            "latitude": 52.52,
            "longitude": 13.405,
            "declination": 30.0,
            "azimuth": 180.0,
            "kw_peak": 9.5,
            "einspeiseverguetung": 0.08,
        }

    async def update_PV(self, pv_id, formData, user, db):
        return {"id": pv_id, "updated": True}

    async def delete_PV(self, pv_id, user, db):
        return {"id": pv_id, "deleted": True}

    async def get_forecast_for_pvs(self, db, pv_owner_id, target_days=None):
        return [{"pv_id": 1, "points": []}]

    async def get_forecast_for_pv(self, db, pv_id, pv_owner_id, target_days=None):
        return {"pv_id": pv_id, "points": []}


class FakeOptimizationService:
    async def run_day_ahead(self, user, db, horizon_days=1, enforce_terminal_bess_soc=None):
        return {
            "status": "ok",
            "horizon_days": horizon_days,
            "enforce_terminal_bess_soc": enforce_terminal_bess_soc,
        }


def auth_headers():
    return {"Authorization": "Bearer test-token"}


def override_current_user():
    return SimpleNamespace(
        id=42,
        name="Test",
        lastname="User",
        username="tester",
        email="tester@example.com",
        annual_consumption_kwh=3500.0,
        load_profile_type="SLP",
    )


def install_common_overrides():
    app.dependency_overrides[auth_service.get_current_user] = override_current_user
    app.dependency_overrides[battery_api.create_class_instance_BESS] = lambda: FakeBESSService()
    app.dependency_overrides[ev_api.create_EV_instance] = lambda: FakeEVService()
    app.dependency_overrides[electricity_api.create_service] = lambda: FakeElectricityService()
    app.dependency_overrides[pv_api.get_pv_service] = lambda: FakePVService()
    app.dependency_overrides[optimization_api.create_service_optimization] = (
        lambda: FakeOptimizationService()
    )
