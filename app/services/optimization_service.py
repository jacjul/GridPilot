from datetime import datetime, timedelta
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
    SLOT_HOURS = 0.25

    @staticmethod
    def _require_float(value: Any, field_name: str, context: str) -> float:
        if value is None:
            raise HTTPException(status_code=422, detail=f"Missing {field_name} for {context}")
        try:
            return float(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"Invalid {field_name} for {context}")

    @staticmethod
    def _is_in_interval(local_t, start_t, end_t) -> bool:
        if start_t <= end_t:
            return start_t <= local_t < end_t
        return local_t >= start_t or local_t < end_t

    def _build_ev_availability(
        self,
        ev: dict[str, Any],
        expected_ts_berlin,
    ) -> list[bool]:
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

    def _build_ev_downtime_start_soc_targets(
        self,
        ev: dict[str, Any],
        expected_ts_berlin,
        availability: list[bool],
    ) -> dict[int, float]:
        rules = ev.get("downtime_rules", [])
        targets: dict[int, float] = {}

        for h in range(1, len(expected_ts_berlin)):
            if availability[h] or not availability[h - 1]:
                continue

            ts = expected_ts_berlin[h]
            local_day = ts.date()
            local_time = ts.timetz().replace(tzinfo=None)
            weekday = ts.weekday()

            active_rule_targets: list[float] = []
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

                if not self._is_in_interval(local_time, rule["start_time"], rule["end_time"]):
                    continue

                target_pct = rule.get("soc_target_start_pct")
                if target_pct is None:
                    continue

                target_fraction = max(0.0, min(1.0, float(target_pct) / 100.0))
                active_rule_targets.append(target_fraction)

            if active_rule_targets:
                targets[h] = max(active_rule_targets)

        return targets

    def _build_ev_downtime_end_soc_targets(
        self,
        ev: dict[str, Any],
        expected_ts_berlin,
        availability: list[bool],
    ) -> dict[int, float]:
        rules = ev.get("downtime_rules", [])
        targets: dict[int, float] = {}

        for h in range(1, len(expected_ts_berlin)):
            if not availability[h] or availability[h - 1]:
                continue

            ts_prev = expected_ts_berlin[h - 1]
            local_day = ts_prev.date()
            local_time = ts_prev.timetz().replace(tzinfo=None)
            weekday = ts_prev.weekday()

            active_rule_targets: list[float] = []
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

                if not self._is_in_interval(local_time, rule["start_time"], rule["end_time"]):
                    continue

                target_pct = rule.get("soc_target_end_pct")
                if target_pct is None:
                    continue

                target_fraction = max(0.0, min(1.0, float(target_pct) / 100.0))
                active_rule_targets.append(target_fraction)

            if active_rule_targets:
                targets[h] = min(active_rule_targets)

        return targets

    @staticmethod
    def _build_daily_demand_vector(annual_kwh: float, load_profile_type: str, steps: int) -> list[float]:
        if annual_kwh <= 0:
            raise HTTPException(status_code=422, detail="annual_consumption_kwh must be > 0")

        # 24-point hourly shape, normalized later to match daily energy.
        if load_profile_type == "SLP_HEATPUMP":
            hourly_shape = [
                0.040, 0.038, 0.036, 0.035, 0.036, 0.040,
                0.047, 0.053, 0.055, 0.052, 0.048, 0.044,
                0.042, 0.041, 0.040, 0.041, 0.044, 0.049,
                0.055, 0.058, 0.058, 0.054, 0.049, 0.044,
            ]
        else:
            hourly_shape = [
                0.030, 0.025, 0.022, 0.020, 0.022, 0.028,
                0.038, 0.048, 0.052, 0.050, 0.047, 0.044,
                0.042, 0.041, 0.040, 0.043, 0.049, 0.058,
                0.067, 0.073, 0.073, 0.064, 0.051, 0.038,
            ]

        quarter_hour_shape = [value / 4.0 for value in hourly_shape for _ in range(4)]
        if steps % len(quarter_hour_shape) != 0:
            raise HTTPException(status_code=500, detail="Demand profile length mismatch")

        shape_sum = sum(quarter_hour_shape)
        if shape_sum <= 0:
            raise HTTPException(status_code=500, detail="Demand profile invalid")

        daily_kwh = annual_kwh / 365.0
        daily_vector = [daily_kwh * (slot_weight / shape_sum) for slot_weight in quarter_hour_shape]
        day_count = steps // len(quarter_hour_shape)
        return daily_vector * day_count

    @staticmethod
    def _normalize_epex_to_ct_per_kwh(raw_prices: list[float]) -> list[float]:
        # Energy-Charts day-ahead prices are provided in EUR/MWh. UI fixed tariff uses ct/kWh.
        # Convert: 1 EUR/MWh = 0.1 ct/kWh.
        return [float(price) / 10.0 for price in raw_prices]

    def _build_pv_kwh_vector(
        self,
        forecasts: list[dict[str, Any]],
        expected_ts_berlin,
        pv_kw_peak_sum: float,
    ) -> list[float]:
        frames = []
        for forecast in forecasts:
            points = forecast.get("points", [])
            if not points:
                continue

            df = pd.DataFrame(points)
            if df.empty or "ts" not in df or "energy_wh" not in df:
                continue

            df_copy = df[["ts", "energy_wh"]].copy()
            df_copy["energy_wh"] = pd.to_numeric(df_copy["energy_wh"], errors="coerce")
            df_copy = df_copy.dropna(subset=["energy_wh"])
            if df_copy.empty:
                continue

            pv_ts = pd.to_datetime(df_copy["ts"], errors="coerce")
            if getattr(pv_ts.dt, "tz", None) is None:
                pv_ts = pv_ts.dt.tz_localize("Europe/Berlin")
            else:
                pv_ts = pv_ts.dt.tz_convert("Europe/Berlin")
            df_copy["ts"] = pv_ts
            frames.append(df_copy)

        if not frames:
            return [0.0] * len(expected_ts_berlin)

        pv_frame = pd.concat(frames, ignore_index=True)
        pv_series_wh = pv_frame.groupby("ts", sort=True)["energy_wh"].sum().sort_index()

        # Some providers return cumulative Wh over day; convert cumulative -> interval Wh.
        diffs = pv_series_wh.diff().dropna()
        is_likely_cumulative = (not diffs.empty) and (diffs >= -1e-6).mean() > 0.95
        if is_likely_cumulative:
            pv_series_wh = pv_series_wh.diff().fillna(pv_series_wh.iloc[0]).clip(lower=0.0)

        pv_series_wh = pv_series_wh.reindex(expected_ts_berlin).interpolate(method="time").fillna(0.0)

        # Convert Wh/slot -> kWh/slot and constrain by physical PV limit with light tolerance.
        kwh_series = (pv_series_wh / 1000.0).clip(lower=0.0)
        max_slot_kwh = max(0.0, pv_kw_peak_sum * self.SLOT_HOURS * 1.2)
        if max_slot_kwh > 0:
            kwh_series = kwh_series.clip(upper=max_slot_kwh)

        return kwh_series.astype(float).tolist()

    def _build_day_advice(
        self,
        status: str,
        prices: list[float],
        kwh_pv: list[float],
        kwh_demand: list[float],
        kwh_grid_entnahme: list[float],
        kwh_grid_einspeisung: list[float],
        kwh_bess_charge: list[float],
        kwh_bess_discharge: list[float],
        kwh_bess_soc: list[float],
        ev_outputs: list[dict[str, Any]],
        ev_specs: list[dict[str, Any]],
        advice_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        advice_context = advice_context or {}
        has_pv = bool(advice_context.get("has_pv", False))
        has_bess = bool(advice_context.get("has_bess", False))
        has_ev = bool(advice_context.get("has_ev", False))
        tariff_type = str(advice_context.get("tariff_type", "unknown"))
        load_profile_type = str(advice_context.get("load_profile_type", "SLP"))
        annual_kwh = float(advice_context.get("annual_consumption_kwh", 0.0) or 0.0)

        total_pv = float(sum(kwh_pv))
        total_demand = float(sum(kwh_demand))
        total_grid_in = float(sum(kwh_grid_entnahme))
        total_grid_out = float(sum(kwh_grid_einspeisung))
        total_bess_throughput = float(sum(kwh_bess_charge) + sum(kwh_bess_discharge))

        price_min = float(min(prices)) if prices else 0.0
        price_max = float(max(prices)) if prices else 0.0
        price_spread = price_max - price_min

        export_share = (total_grid_out / total_pv) if total_pv > 0 else 0.0
        import_share = (total_grid_in / total_demand) if total_demand > 0 else 0.0

        soc_swing = (max(kwh_bess_soc) - min(kwh_bess_soc)) if kwh_bess_soc else 0.0
        soc_end = kwh_bess_soc[-1] if kwh_bess_soc else 0.0

        import_baseline = 0.75
        if has_pv:
            import_baseline -= 0.18
        if has_bess:
            import_baseline -= 0.10
        if load_profile_type == "SLP_HEATPUMP":
            import_baseline += 0.08
        import_baseline = max(0.35, min(0.9, import_baseline))

        export_baseline = 0.28
        if has_ev:
            export_baseline -= 0.08
        if has_bess:
            export_baseline -= 0.08
        if not has_pv:
            export_baseline = 1.0
        export_baseline = max(0.08, min(0.85, export_baseline))

        candidates: list[tuple[float, str]] = []
        if status != "Optimal":
            candidates.append(
                (
                    100.0,
                    "Plan reliability warning: the optimizer did not find an optimal plan. Treat today's schedule as tentative and relax tight constraints first.",
                )
            )

        if import_share > import_baseline:
            if has_bess:
                import_action = "use your battery more aggressively in low-price slots"
            elif has_ev:
                import_action = "shift EV charging away from expensive windows"
            else:
                import_action = "shift flexible household loads to cheaper periods"
            candidates.append(
                (
                    (import_share - import_baseline) * 120.0,
                    (
                        f"Main cost driver today: {total_grid_in:.1f} kWh grid import "
                        f"({import_share * 100.0:.0f}% of demand). Biggest lever for your setup: {import_action}."
                    ),
                )
            )

        if total_pv > 0 and export_share > export_baseline:
            if has_bess and has_ev:
                export_action = "charge EV and BESS around midday to keep more solar on-site"
            elif has_bess:
                export_action = "fill the battery earlier around solar peak"
            elif has_ev:
                export_action = "schedule more EV charging in solar hours"
            else:
                export_action = "move shiftable loads (e.g. hot water, appliances) into midday"
            candidates.append(
                (
                    (export_share - export_baseline) * 110.0,
                    (
                        f"Solar surplus stands out: {total_grid_out:.1f} kWh exported "
                        f"({export_share * 100.0:.0f}% of PV). For your assets, best next step: {export_action}."
                    ),
                )
            )

        if tariff_type == "dynamic_EPEX" and price_spread >= 10 and total_bess_throughput < 0.25 * max(total_demand, 1e-9):
            candidates.append(
                (
                    price_spread,
                    (
                        f"Price swings are high ({price_spread:.1f} ct/kWh), but battery shifting is low "
                        f"({total_bess_throughput:.1f} kWh moved). Increasing BESS use in cheap windows can cut peak-hour buying."
                    ),
                )
            )

        if soc_swing < 0.3 and (total_bess_throughput > 0 or (price_spread >= 10 and total_demand > 0)):
            candidates.append(
                (
                    (0.3 - soc_swing) * 20.0,
                    (
                        f"Battery is barely active (SOC swing {soc_swing:.2f} kWh). Check power limits and control targets so it can shift more energy when needed."
                    ),
                )
            )

        ev_capacity_by_id = {int(ev["id"]): float(ev["capacity_kwh"]) for ev in ev_specs}
        low_ev_final_soc: list[int] = []
        low_ev_final_soc_detail: list[str] = []
        for ev in ev_outputs:
            ev_id = int(ev["ev_id"])
            capacity = ev_capacity_by_id.get(ev_id, 0.0)
            final_soc = float(ev["kwh_soc"][-1]) if ev.get("kwh_soc") else 0.0
            final_soc_pct = (final_soc / capacity * 100.0) if capacity > 0 else 0.0
            if final_soc_pct < 60.0:
                low_ev_final_soc.append(ev_id)
                low_ev_final_soc_detail.append(f"EV {ev_id}: {final_soc_pct:.0f}%")

        if low_ev_final_soc:
            candidates.append(
                (
                    35.0 + len(low_ev_final_soc) * 8.0,
                    (
                        "EV readiness risk: "
                        + ", ".join(low_ev_final_soc_detail)
                        + ". Raise downtime target SOC or widen charging windows."
                    ),
                )
            )

        if annual_kwh >= 7000 and import_share > max(import_baseline, 0.55):
            candidates.append(
                (
                    20.0,
                    (
                        f"Your annual demand is high ({annual_kwh:.0f} kWh/a), so daily import costs have stronger impact. "
                        "Running one extra compare scenario focused on load shifting can deliver visible savings."
                    ),
                )
            )

        candidates = sorted(candidates, key=lambda entry: entry[0], reverse=True)
        items = [text for _score, text in candidates[:3]]

        if len(items) < 2:
            if total_pv > 0 and import_share <= 0.50:
                items.append(
                    f"Strong self-supply today: grid import is only {import_share * 100.0:.0f}% of demand. Current setup is working well."
                )
            else:
                items.append(
                    "No major risk stands out today. Keep this setup and use this run as your baseline scenario."
                )

        if len(items) < 2:
            items.append(
                "Focus first on one lever for tomorrow: either reduce grid import share or increase EV final SOC targets."
            )

        summary = "Top daily takeaways tailored to your setup (assets, tariff, and load profile)."
        return {
            "summary": summary,
            "items": items,
            "metrics": {
                "price_min_ct_kwh": price_min,
                "price_max_ct_kwh": price_max,
                "price_spread_ct_kwh": price_spread,
                "total_pv_kwh": total_pv,
                "total_demand_kwh": total_demand,
                "total_grid_import_kwh": total_grid_in,
                "total_grid_export_kwh": total_grid_out,
                "export_share_of_pv": export_share,
                "import_share_of_demand": import_share,
                "total_bess_throughput_kwh": total_bess_throughput,
                "bess_soc_swing_kwh": soc_swing,
                "bess_end_soc_kwh": soc_end,
            },
        }

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
                "annual_consumption_kwh": float(current_user.annual_consumption_kwh),
                "load_profile_type": current_user.load_profile_type,
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
                            "soc_target_start_pct": rule.soc_target_start_pct,
                            "soc_target_end_pct": rule.soc_target_end_pct,
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

    async def run_day_ahead(
        self,
        user: UserMe,
        db: AsyncSession,
        horizon_days: int = 1,
        enforce_terminal_bess_soc: bool | None = None,
    ):
        if horizon_days not in (1, 2):
            raise HTTPException(status_code=422, detail="horizon_days must be 1 or 2")

        if enforce_terminal_bess_soc is None:
            enforce_terminal_bess_soc = horizon_days == 1

        current_user = await self._load_current_user(user_id=user.id, db=db)
        optimizer_input = self._build_optimizer_input(current_user)

        photovoltaik = optimizer_input.get("photovoltaik", [])
        electric_vehicles = optimizer_input.get("electric_vehicles", [])
        batteries = optimizer_input.get("batteries", [])
        electricity_prices = optimizer_input.get("electricity_prices", [])
        user_config = optimizer_input.get("user", {})

        has_pv = bool(photovoltaik)
        has_bess = bool(batteries)
        has_ev = bool(electric_vehicles)

        if not electricity_prices:
            raise HTTPException(status_code=404, detail="an electricity tarif is necessary")

        steps = 96 * horizon_days
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

            dynamic_prices_ct_per_kwh = self._normalize_epex_to_ct_per_kwh(dynamic_prices)
            df = pd.DataFrame({"ts": timestamps, "price": dynamic_prices_ct_per_kwh})
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
        pv_kw_peak_sum = 0.0
        soc_initial_bess = soc_final_bess = 0.0
        if has_bess:
            for bess in batteries:
                bess_id = bess.get("id", "unknown")
                context = f"battery #{bess_id}"
                kw_peak_charge += self._require_float(bess.get("kw_peak_charge"), "kw_peak_charge", context)
                kw_peak_discharge += self._require_float(
                    bess.get("kw_peak_discharge"), "kw_peak_discharge", context
                )
                kwh_bess += self._require_float(bess.get("kwh"), "kwh", context)
            soc_initial_bess = soc_final_bess = 0.4 * kwh_bess

        ev_specs: list[dict[str, Any]] = []
        for ev in electric_vehicles:
            ev_id = int(ev["id"])
            context = f"EV #{ev_id}"
            availability = self._build_ev_availability(ev, expected_ts_berlin)
            ev_specs.append(
                {
                    "id": ev_id,
                    "capacity_kwh": self._require_float(ev.get("kwh_battery"), "kwh_battery", context),
                    "charge_power_kw": self._require_float(
                        ev.get("kw_peak_loading"), "kw_peak_loading", context
                    ),
                    "available": availability,
                    "downtime_start_soc_targets": self._build_ev_downtime_start_soc_targets(
                        ev,
                        expected_ts_berlin,
                        availability,
                    ),
                    "downtime_end_soc_targets": self._build_ev_downtime_end_soc_targets(
                        ev,
                        expected_ts_berlin,
                        availability,
                    ),
                }
            )

        prices_einspeisung: list[float] = [0.0] * steps
        if has_pv:
            pv_service = PVForecastService()
            lists_pv: list[PVOut] = await pv_service.get_PV_data(user, db)
            summed_verguetung = 0.0
            for pv in lists_pv:
                summed_verguetung += float(pv.kw_peak) * float(pv.einspeiseverguetung)
                pv_kw_peak_sum += float(pv.kw_peak)
            avg_einspeiseverguetung = (summed_verguetung / pv_kw_peak_sum) if pv_kw_peak_sum > 0 else 0.0
            prices_einspeisung = [avg_einspeiseverguetung] * steps

            target_days = [optimization_day + timedelta(days=offset) for offset in range(horizon_days)]
            forecasts = await pv_service.get_forecast_for_pvs(
                db=db,
                pv_owner_id=user.id,
                target_days=target_days,
            )
            kwh_pv = self._build_pv_kwh_vector(
                forecasts=forecasts,
                expected_ts_berlin=expected_ts_berlin,
                pv_kw_peak_sum=pv_kw_peak_sum,
            )

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

        annual_consumption_kwh = float(user_config.get("annual_consumption_kwh", 3500.0))
        load_profile_type = str(user_config.get("load_profile_type", "SLP"))
        kwh_demand = self._build_daily_demand_vector(
            annual_kwh=annual_consumption_kwh,
            load_profile_type=load_profile_type,
            steps=steps,
        )

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
            downtime_start_soc_targets = ev.get("downtime_start_soc_targets", {})
            downtime_end_soc_targets = ev.get("downtime_end_soc_targets", {})

            model += ev_soc[ev_id][0] == 0.3 * capacity

            for h in hours:
                if not availability[h]:
                    model += ev_charge[ev_id][h] == 0

            for h in hours:
                if h == 0:
                    continue

                if availability[h] and not availability[h - 1]:
                    if h in downtime_end_soc_targets:
                        model += ev_soc[ev_id][h] == downtime_end_soc_targets[h] * capacity
                    else:
                        model += ev_soc[ev_id][h] == 0.2 * capacity
                    model += ev_charge[ev_id][h] == 0
                elif not availability[h]:
                    model += ev_soc[ev_id][h] == ev_soc[ev_id][h - 1]
                else:
                    model += ev_soc[ev_id][h] == ev_soc[ev_id][h - 1] + ev_charge[ev_id][h]

                if h in downtime_start_soc_targets:
                    model += ev_soc[ev_id][h] >= downtime_start_soc_targets[h] * capacity

            model += ev_soc[ev_id][steps - 1] >= 0.5 * capacity

        if has_bess:
            if enforce_terminal_bess_soc:
                model += kwh_bess_gespeichert[steps - 1] == soc_final_bess
            else:
                model += kwh_bess_gespeichert[steps - 1] >= 0.1 * kwh_bess

        solved = model.solve(PULP_CBC_CMD(msg=False))
        status = LpStatus.get(model.status, "Unknown")

        grid_entnahme = [value(kwh_grid_entnahme[h]) for h in hours]
        grid_einspeisung = [value(kwh_grid_einspeisung[h]) for h in hours]
        bess_charge = [value(kwh_bess_charge[h]) for h in hours]
        bess_discharge = [value(kwh_bess_discharge[h]) for h in hours]
        bess_soc = [value(kwh_bess_gespeichert[h]) for h in hours]
        ev_output = [
            {
                "ev_id": ev["id"],
                "available": ev["available"],
                "kwh_charge": [value(ev_charge[ev["id"]][h]) for h in hours],
                "kwh_soc": [value(ev_soc[ev["id"]][h]) for h in hours],
            }
            for ev in ev_specs
        ]

        day_advice = self._build_day_advice(
            status=status,
            prices=prices,
            kwh_pv=kwh_pv,
            kwh_demand=kwh_demand,
            kwh_grid_entnahme=grid_entnahme,
            kwh_grid_einspeisung=grid_einspeisung,
            kwh_bess_charge=bess_charge,
            kwh_bess_discharge=bess_discharge,
            kwh_bess_soc=bess_soc,
            ev_outputs=ev_output,
            ev_specs=ev_specs,
            advice_context={
                "has_pv": has_pv,
                "has_bess": has_bess,
                "has_ev": has_ev,
                "tariff_type": active_electricity.get("price_typ"),
                "load_profile_type": load_profile_type,
                "annual_consumption_kwh": annual_consumption_kwh,
                "bess_capacity_kwh": kwh_bess,
                "pv_kw_peak_sum": pv_kw_peak_sum,
            },
        )

        return {
            "status": status,
            "solver_code": solved,
            "horizon_days": horizon_days,
            "bess_terminal_soc_policy": "strict_40pct" if enforce_terminal_bess_soc else "relaxed_min_10pct",
            "objective": value(model.objective),
            "timestamps": [ts.isoformat() for ts in expected_ts_berlin],
            "prices": prices,
            "kwh_pv": kwh_pv,
            "kwh_demand": kwh_demand,
            "kwh_grid_entnahme": grid_entnahme,
            "kwh_grid_einspeisung": grid_einspeisung,
            "kwh_bess_charge": bess_charge,
            "kwh_bess_discharge": bess_discharge,
            "kwh_bess_soc": bess_soc,
            "ev": ev_output,
            "day_advice": day_advice,
        }
