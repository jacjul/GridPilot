from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import HTTPException
from pulp import LpMinimize, LpProblem, LpStatus, LpVariable, PULP_CBC_CMD, lpSum, value
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.electric_vehicle import ElectricVehicle
from app.models.user import User
from app.schemas.photovoltaik import PVOut
from app.schemas.user import UserMe
from app.services.electricity_service import ElectricityService
from app.services.photovoltaik_service import PVForecastService


class OptimizationService:
    @staticmethod
    def _is_in_interval(local_t, start_t, end_t) -> bool:
        if start_t <= end_t:
            return start_t <= local_t < end_t
        return local_t >= start_t or local_t < end_t

    def _build_ev_availability(self, ev: dict[str, Any], expected_ts_berlin) -> list[bool]:
        rules = ev.get("downtime_rules", [])
        exceptions = ev.get("downtime_exceptions", [])
        availability: list[bool] = [True] * len(expected_ts_berlin)

        for h, ts in enumerate(expected_ts_berlin):
            unavailable = False
            local_day = ts.date()
            local_time = ts.timetz().replace(tzinfo=None)
            weekday = ts.weekday()

            for rule in rules:
                valid_from = rule.get("valid_from")
                valid_to = rule.get("valid_to")
                if valid_from is not None and local_day < valid_from:
                    continue
                if valid_to is not None and local_day > valid_to:
                    continue

                mask = int(rule.get("weekdays_mask", 0))
                if not (mask & (1 << weekday)):
                    continue

                if self._is_in_interval(local_time, rule["start_time"], rule["end_time"]):
                    unavailable = True
                    break

            if not unavailable:
                for ex in exceptions:
                    if ex.get("day") != local_day:
                        continue
                    if self._is_in_interval(local_time, ex["start_time"], ex["end_time"]):
                        unavailable = True
                        break

            availability[h] = not unavailable

        return availability

    async def _load_current_user(self, user_id: int, db: AsyncSession):
        stmt = (
            select(User)
            .options(
                selectinload(User.electric_vehicle_owned).selectinload(ElectricVehicle.downtime_rules),
                selectinload(User.electric_vehicle_owned).selectinload(ElectricVehicle.downtime_exceptions),
                selectinload(User.battery_owned),
                selectinload(User.photovoltaik_owned),
                selectinload(User.electricity_owned),
            )
            .where(User.id == user_id)
        )

        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    def _build_optimizer_input(self, current_user: User) -> dict[str, Any]:
        return {
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "lastname": current_user.lastname,
                "username": current_user.username,
            },
            "photovoltaik": [
                {
                    "id": pv.id,
                    "latitude": pv.latitude,
                    "longitude": pv.longitude,
                    "declination": pv.declination,
                    "azimuth": pv.azimuth,
                    "kw_peak": pv.kw_peak,
                }
                for pv in current_user.photovoltaik_owned
            ],
            "electric_vehicles": [
                {
                    "id": ev.id,
                    "ev_name": ev.ev_name,
                    "kw_peak_loading": ev.kw_peak_loading,
                    "kwh_battery": ev.kwh_battery,
                    "downtime_rules": [
                        {
                            "id": rule.id,
                            "weekdays_mask": rule.weekdays_mask,
                            "start_time": rule.start_time,
                            "end_time": rule.end_time,
                            "valid_from": rule.valid_from,
                            "valid_to": rule.valid_to,
                            "tz_name": rule.tz_name,
                        }
                        for rule in ev.downtime_rules
                    ],
                    "downtime_exceptions": [
                        {
                            "id": ex.id,
                            "day": ex.day,
                            "start_time": ex.start_time,
                            "end_time": ex.end_time,
                        }
                        for ex in ev.downtime_exceptions
                    ],
                }
                for ev in current_user.electric_vehicle_owned
            ],
            "batteries": [
                {
                    "id": battery.id,
                    "name": battery.name,
                    "kw_peak_charge": battery.kw_peak_charge,
                    "kw_peak_discharge": battery.kw_peak_discharge,
                    "kwh": battery.kwh,
                }
                for battery in current_user.battery_owned
            ],
            "electricity_prices": [
                {
                    "name": price.name,
                    "price_typ": price.price_typ,
                    "fixed_price": price.fixed_price,
                    "is_active": price.is_active,
                    "market_zone": price.market_zone,
                }
                for price in current_user.electricity_owned
            ],
        }

    async def run_day_ahead(self, user: UserMe, db: AsyncSession):
        current_user = await self._load_current_user(user_id=user.id, db=db)
        optimizer_input = self._build_optimizer_input(current_user)

        photovoltaik = optimizer_input.get("photovoltaik", [])
        electric_vehicles = optimizer_input.get("electric_vehicles", [])
        batteries = optimizer_input.get("batteries", [])
        electricity_prices = optimizer_input.get("electricity_prices", [])

        has_pv = bool(photovoltaik)
        has_bess = bool(batteries)

        if not electricity_prices:
            raise HTTPException(status_code=404, detail="an electricity tarif is necessary")

        steps = 96
        hours = range(steps)
        prices: list[float] = [0.0] * steps
        kwh_pv: list[float] = [0.0] * steps
        optimization_day = datetime.now(ZoneInfo("Europe/Berlin")).date()
        start_ts_berlin = pd.Timestamp(optimization_day).tz_localize("Europe/Berlin")
        expected_ts_berlin = pd.date_range(start=start_ts_berlin, periods=steps, freq="15min")

        active_electricity = next((tariff for tariff in electricity_prices if tariff.get("is_active") is True), None)
        if active_electricity is None:
            raise HTTPException(status_code=400, detail="No active electricity tariff found")

        if active_electricity["price_typ"] == "fixed" and active_electricity["fixed_price"] is not None:
            prices = [float(active_electricity["fixed_price"])] * steps
        elif active_electricity["price_typ"] == "dynamic_EPEX":
            electricity_service = ElectricityService()
            dynamic_points = await electricity_service.get_current_DynamicPricePoints(user, db)
            timestamps = dynamic_points.timestamps
            dynamic_prices = dynamic_points.prices

            if len(timestamps) != len(dynamic_prices):
                raise HTTPException(status_code=502, detail="Dynamic price data length mismatch")
            if not timestamps:
                raise HTTPException(status_code=503, detail="No dynamic prices available")

            df = pd.DataFrame({"ts": timestamps, "price": dynamic_prices})
            df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Europe/Berlin")
            df = df.sort_values("ts")

            price_series = (
                df.set_index("ts")["price"]
                .reindex(expected_ts_berlin)
                .interpolate(method="time")
                .ffill()
                .bfill()
            )
            prices = price_series.astype(float).tolist()
        else:
            raise HTTPException(status_code=422, detail="Unsupported electricity price type")

        kw_peak_charge = kw_peak_discharge = kwh_bess = 0.0
        soc_initial_bess = soc_final_bess = 0.0
        if has_bess:
            for bess in batteries:
                kw_peak_charge += float(bess["kw_peak_charge"])
                kw_peak_discharge += float(bess["kw_peak_discharge"])
                kwh_bess += float(bess["kwh"])
            soc_initial_bess = soc_final_bess = 0.4 * kwh_bess

        ev_specs: list[dict[str, Any]] = []
        for ev in electric_vehicles:
            ev_specs.append(
                {
                    "id": int(ev["id"]),
                    "capacity_kwh": float(ev["kwh_battery"]),
                    "charge_power_kw": float(ev["kw_peak_loading"]),
                    "available": self._build_ev_availability(ev, expected_ts_berlin),
                }
            )

        prices_einspeisung: list[float] = [0.0] * steps
        if has_pv:
            pv_service = PVForecastService()
            lists_pv: list[PVOut] = await pv_service.get_PV_data(user, db)
            summed_verguetung = 0.0
            pv_kw_peak_sum = 0.0
            for pv in lists_pv:
                summed_verguetung += float(pv.kw_peak) * float(pv.einspeiseverguetung)
                pv_kw_peak_sum += float(pv.kw_peak)
            avg_einspeiseverguetung = (summed_verguetung / pv_kw_peak_sum) if pv_kw_peak_sum > 0 else 0.0
            prices_einspeisung = [avg_einspeiseverguetung] * steps

            forecasts = await pv_service.get_forecast_for_pvs(db=db, pv_owner_id=user.id, target_days=None)
            pv_frames = []
            for forecast in forecasts:
                points = forecast.get("points", [])
                if not points:
                    continue

                df = pd.DataFrame(points)
                if df.empty:
                    continue

                df_copy = df[["ts", "energy_wh"]].copy()
                pv_ts = pd.to_datetime(df["ts"], errors="coerce")
                if getattr(pv_ts.dt, "tz", None) is None:
                    pv_ts = pv_ts.dt.tz_localize("Europe/Berlin")
                else:
                    pv_ts = pv_ts.dt.tz_convert("Europe/Berlin")
                df_copy["ts"] = pv_ts
                pv_frames.append(df_copy)

            if pv_frames:
                pv_frame = pd.concat(pv_frames, ignore_index=True)
                pv_day = pv_frame.groupby("ts", as_index=False, sort=True)["energy_wh"].sum()
                pv_day["energy_kwh"] = pv_day["energy_wh"] / 1000.0
                pv_day = (
                    pv_day.set_index(pv_day["ts"])
                    .reindex(expected_ts_berlin)
                    .interpolate(method="linear")
                    .rename_axis("ts")
                    .reset_index()
                )
                kwh_pv = pv_day["energy_kwh"].fillna(0.0).astype(float).tolist()

        model = LpProblem("HEMS", LpMinimize)

        kwh_grid_entnahme = LpVariable.dicts("kwh_grid_entnahme", hours, lowBound=0)
        if has_pv:
            kwh_grid_einspeisung = LpVariable.dicts("kwh_grid_einspeisung", hours, lowBound=0)
        else:
            kwh_grid_einspeisung = LpVariable.dicts("kwh_grid_einspeisung", hours, lowBound=0, upBound=0)

        grid_is_entnahme = LpVariable.dicts("grid_is_entnahme", hours, lowBound=0, upBound=1, cat="Binary")

        upbound_charge_bess = kw_peak_charge * 0.25
        upbound_discharge_bess = kw_peak_discharge * 0.25
        kwh_bess_discharge = LpVariable.dicts(
            "kwh_bess_discharge", hours, lowBound=0, upBound=upbound_discharge_bess
        )
        kwh_bess_charge = LpVariable.dicts(
            "kwh_bess_charge", hours, lowBound=0, upBound=upbound_charge_bess
        )
        bess_is_charging = LpVariable.dicts(
            "binary_bess_is_charging", hours, lowBound=0, upBound=1, cat="Binary"
        )
        kwh_bess_gespeichert = LpVariable.dicts("Speicher_BESS", hours, lowBound=0, upBound=kwh_bess)

        ev_charge: dict[int, dict[int, LpVariable]] = {}
        ev_soc: dict[int, dict[int, LpVariable]] = {}
        for ev in ev_specs:
            ev_id = ev["id"]
            ev_charge[ev_id] = LpVariable.dicts(
                f"kwh_ev_charge_{ev_id}",
                hours,
                lowBound=0,
                upBound=ev["charge_power_kw"] * 0.25,
            )
            ev_soc[ev_id] = LpVariable.dicts(
                f"kwh_ev_soc_{ev_id}",
                hours,
                lowBound=0,
                upBound=ev["capacity_kwh"],
            )

        kwh_demand = [5.0] * steps

        model += lpSum(
            prices[h] * kwh_grid_entnahme[h] - prices_einspeisung[h] * kwh_grid_einspeisung[h]
            for h in hours
        )

        for h in hours:
            model += (
                kwh_bess_discharge[h]
                + kwh_grid_entnahme[h]
                + kwh_pv[h]
                == kwh_grid_einspeisung[h]
                + kwh_demand[h]
                + kwh_bess_charge[h]
                + lpSum(ev_charge[ev["id"]][h] for ev in ev_specs)
            )

        model += kwh_bess_gespeichert[0] == soc_initial_bess
        for h in hours:
            if h > 0:
                model += (
                    kwh_bess_gespeichert[h]
                    == kwh_bess_gespeichert[h - 1] + kwh_bess_charge[h] - kwh_bess_discharge[h]
                )

        for h in hours:
            model += kwh_bess_charge[h] <= upbound_charge_bess * bess_is_charging[h]
            model += kwh_bess_discharge[h] <= upbound_discharge_bess * (1 - bess_is_charging[h])

        for h in hours:
            model += kwh_grid_entnahme[h] <= 20 * grid_is_entnahme[h]
            model += kwh_grid_einspeisung[h] <= 20 * (1 - grid_is_entnahme[h])

        for ev in ev_specs:
            ev_id = ev["id"]
            availability = ev["available"]
            capacity = ev["capacity_kwh"]

            model += ev_soc[ev_id][0] == 0.3 * capacity

            for h in hours:
                if not availability[h]:
                    model += ev_charge[ev_id][h] == 0

            for h in hours:
                if h == 0:
                    continue

                if availability[h] and not availability[h - 1]:
                    model += ev_soc[ev_id][h] == 0.2 * capacity
                    model += ev_charge[ev_id][h] == 0
                elif not availability[h]:
                    model += ev_soc[ev_id][h] == ev_soc[ev_id][h - 1]
                else:
                    model += ev_soc[ev_id][h] == ev_soc[ev_id][h - 1] + ev_charge[ev_id][h]

            model += ev_soc[ev_id][steps - 1] >= 0.5 * capacity

        model += kwh_bess_gespeichert[steps - 1] == soc_final_bess

        solved = model.solve(PULP_CBC_CMD(msg=False))
        status = LpStatus.get(model.status, "Unknown")

        return {
            "status": status,
            "solver_code": solved,
            "objective": value(model.objective),
            "timestamps": [ts.isoformat() for ts in expected_ts_berlin],
            "prices": prices,
            "kwh_pv": kwh_pv,
            "kwh_grid_entnahme": [value(kwh_grid_entnahme[h]) for h in hours],
            "kwh_grid_einspeisung": [value(kwh_grid_einspeisung[h]) for h in hours],
            "kwh_bess_charge": [value(kwh_bess_charge[h]) for h in hours],
            "kwh_bess_discharge": [value(kwh_bess_discharge[h]) for h in hours],
            "kwh_bess_soc": [value(kwh_bess_gespeichert[h]) for h in hours],
            "ev": [
                {
                    "ev_id": ev["id"],
                    "available": ev["available"],
                    "kwh_charge": [value(ev_charge[ev["id"]][h]) for h in hours],
                    "kwh_soc": [value(ev_soc[ev["id"]][h]) for h in hours],
                }
                for ev in ev_specs
            ],
        }
