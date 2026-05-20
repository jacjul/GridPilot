from sqlalchemy import select, and_, update, delete
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta, time
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd 

from app.models.photovoltaik import Photovoltaik
from app.models.PV_forecast import PVForecastRun, PVForecastPoint
from app.schemas.user import UserMe
from app.schemas.photovoltaik import PVform,PVOut,PVUpdateForm


class PVForecastService:
    BASE_URL = "https://api.forecast.solar/estimate/watthours"
    PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
    GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
    SUN_API_URL = "https://api.sunrise-sunset.org/json"
    MIN_SUNRISE_TIME = time(4, 30)
    MAX_SUNSET_TIME = time(22, 30)

    @staticmethod
    def _merge_points_keep_lowest_energy(
        points: list[tuple[datetime, float]],
    ) -> list[tuple[datetime, float]]:
        # Keep one point per timestamp and prefer lower energy so zero anchors win.
        merged: dict[datetime, float] = {}
        for ts, energy in points:
            if ts in merged:
                merged[ts] = min(merged[ts], float(energy))
            else:
                merged[ts] = float(energy)
        return sorted(merged.items(), key=lambda item: item[0])

    def _default_target_days(self) -> list[date]:
        today_berlin = datetime.now(ZoneInfo("Europe/Berlin")).date()
        return [today_berlin, today_berlin + timedelta(days=1)]

    async def _resolve_place_to_coordinates(self, place: str) -> tuple[float, float]:
        params = {"q": place, "format": "jsonv2", "limit": 1}
        headers = {"User-Agent": "GridPilot/1.0"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.GEOCODE_URL, params=params, headers=headers)
                response.raise_for_status()
            except httpx.HTTPStatusError:
                raise HTTPException(status_code=502, detail="Geocoding provider returned an error")
            except httpx.RequestError:
                raise HTTPException(status_code=503, detail="Geocoding provider unreachable")

        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise HTTPException(status_code=422, detail="Could not resolve place to coordinates")

        best = payload[0]
        try:
            lat = float(best["lat"])
            lon = float(best["lon"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=502, detail="Invalid geocoding response")

        return lat, lon

    async def create_new_PV(self, formdata: PVform, user: UserMe, db: AsyncSession):
        latitude, longitude = await self._resolve_place_to_coordinates(formdata.place)

        new_pv = Photovoltaik(
            latitude=latitude,
            longitude=longitude,
            declination=formdata.declination,
            azimuth=formdata.azimuth,
            kw_peak=formdata.kw_peak,
            einspeiseverguetung=formdata.einspeiseverguetung,
            owner_id=user.id,
        )

        try:
            db.add(new_pv)
            await db.commit()
            await db.refresh(new_pv)
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not add the PV")
        return {"message": "success", "latitude": latitude, "longitude": longitude}

    async def _assert_user_owns_pv(self, pv_id: int, user_id: int, db: AsyncSession) -> Photovoltaik:
        result = await db.execute(
            select(Photovoltaik).where(
                and_(Photovoltaik.id == pv_id, Photovoltaik.owner_id == user_id)
            )
        )
        pv = result.scalar_one_or_none()
        if pv is None:
            raise HTTPException(status_code=404, detail="Could not find PV")
        return pv

    async def get_PV_data(self,user:UserMe, db:AsyncSession)-> list[PVOut]:
        result = await db.execute(select(Photovoltaik).where(Photovoltaik.owner_id ==user.id))
        rows = result.scalars().all()
        return [PVOut.model_validate(row) for row in rows]

    async def get_single_PV(self, pv_id: int, user: UserMe, db: AsyncSession) -> PVOut:
        pv = await self._assert_user_owns_pv(pv_id, user.id, db)
        return PVOut.model_validate(pv)

    async def update_PV(self, pv_id: int, formdata: PVUpdateForm, user: UserMe, db: AsyncSession):
        await self._assert_user_owns_pv(pv_id, user.id, db)

        patch_data = formdata.model_dump(exclude_unset=True, exclude_none=True)
        if not patch_data:
            raise HTTPException(status_code=400, detail="No update data provided")

        if "place" in patch_data:
            latitude, longitude = await self._resolve_place_to_coordinates(patch_data.pop("place"))
            patch_data.update({"latitude": latitude, "longitude": longitude})

        patch_data["updated_at"] = datetime.now(ZoneInfo("Europe/Berlin"))

        try:
            await db.execute(
                update(Photovoltaik)
                .where(and_(Photovoltaik.id == pv_id, Photovoltaik.owner_id == user.id))
                .values(**patch_data)
            )
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not update PV")

        return {"message": "success", "pv_id": pv_id}

    async def delete_PV(self, pv_id: int, user: UserMe, db: AsyncSession):
        await self._assert_user_owns_pv(pv_id, user.id, db)
        try:
            await db.execute(
                delete(Photovoltaik)
                .where(and_(Photovoltaik.id == pv_id, Photovoltaik.owner_id == user.id))
            )
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not delete PV")

        return {"message": "success", "pv_id": pv_id}

    async def _fetch_data_api_forecast_solar(self, latitude, longitude, declination, azimuth, kwp):
        url = f"{self.BASE_URL}/{latitude}/{longitude}/{declination}/{azimuth}/{kwp}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        result = payload.get("result")
        if isinstance(result, list):
            return result[0] if result else {}
        if isinstance(result, dict):
            return result
        raise ValueError("Unexpected forecast.solar response")

    @staticmethod
    def _parse_pvgis_power_w(hour_entry: dict) -> float | None:
        for key in ("P", "Pdc", "P_AC", "power"):
            value = hour_entry.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return None

    async def _fetch_data_api_pvgis_fallback(self, latitude, longitude, declination, azimuth, kwp):
        now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
        candidate_years = [
            now_berlin.year - 1,
            now_berlin.year - 2,
            now_berlin.year - 3,
            2020,
            2019,
            2018,
        ]
        # Keep order, remove duplicates, and ignore invalid years.
        unique_years: list[int] = []
        for year in candidate_years:
            if year >= 2005 and year not in unique_years:
                unique_years.append(year)

        payload = None
        async with httpx.AsyncClient(timeout=15.0) as client:
            last_error: Exception | None = None
            for year in unique_years:
                pvgis_params = {
                    "lat": latitude,
                    "lon": longitude,
                    "startyear": year,
                    "endyear": year,
                    "pvcalculation": 1,
                    "peakpower": kwp,
                    "loss": 14,
                    "angle": declination,
                    "aspect": azimuth,
                    "outputformat": "json",
                }

                try:
                    response = await client.get(self.PVGIS_URL, params=pvgis_params)
                    response.raise_for_status()
                    payload = response.json()
                    break
                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    last_error = exc
                    continue

            if payload is None:
                if last_error:
                    raise last_error
                raise ValueError("PVGIS fallback could not fetch data")

        outputs = payload.get("outputs", {})
        hourly = outputs.get("hourly")
        if not isinstance(hourly, list) or not hourly:
            raise ValueError("Unexpected PVGIS response")

        lookup_by_month_day_hour: dict[tuple[int, int, int], float] = {}
        for row in hourly:
            if not isinstance(row, dict):
                continue
            time_raw = row.get("time")
            if not isinstance(time_raw, str):
                continue
            try:
                row_ts = datetime.strptime(time_raw, "%Y%m%d:%H%M")
            except ValueError:
                continue

            power_w = self._parse_pvgis_power_w(row)
            if power_w is None:
                continue

            key = (row_ts.month, row_ts.day, row_ts.hour)
            lookup_by_month_day_hour[key] = max(0.0, power_w)

        if not lookup_by_month_day_hour:
            raise ValueError("PVGIS fallback had no usable hourly values")

        result: dict[str, float] = {}
        horizon_hours = 48
        start_hour = now_berlin.replace(hour=0, minute=0, second=0, microsecond=0)
        for offset in range(horizon_hours):
            ts = start_hour + timedelta(hours=offset)
            key = (ts.month, ts.day, ts.hour)
            power_w = lookup_by_month_day_hour.get(key, 0.0)
            energy_wh = max(0.0, power_w)
            result[ts.strftime("%Y-%m-%d %H:%M:%S")] = energy_wh

        if not result:
            raise ValueError("PVGIS fallback could not build forecast")

        return result

    async def fetch_data_api(self, latitude, longitude, declination, azimuth, kwp) -> tuple[dict[str, float], str]:
        try:
            forecast = await self._fetch_data_api_forecast_solar(
                latitude,
                longitude,
                declination,
                azimuth,
                kwp,
            )
            return forecast, "forecast.solar"
        except (httpx.HTTPStatusError, httpx.RequestError, ValueError):
            pass

        try:
            forecast = await self._fetch_data_api_pvgis_fallback(
                latitude,
                longitude,
                declination,
                azimuth,
                kwp,
            )
            return forecast, "pvgis_fallback"
        except (httpx.HTTPStatusError, httpx.RequestError, ValueError):
            raise HTTPException(status_code=503, detail="Both PV forecast providers are unavailable")

    async def _fetch_sunrise_sunset_for_day(
        self,
        latitude: float,
        longitude: float,
        day: date,
    ) -> tuple[datetime, datetime]:
        params = {
            "lat": latitude,
            "lng": longitude,
            "date": day.isoformat(),
            "formatted": 0,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.SUN_API_URL, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError:
                raise HTTPException(status_code=502, detail="Sun provider returned an error")
            except httpx.RequestError:
                raise HTTPException(status_code=503, detail="Sun provider unreachable")

        payload = response.json()
        if payload.get("status") != "OK":
            raise HTTPException(status_code=502, detail="Invalid sunrise/sunset response")

        result = payload.get("results")
        if not isinstance(result, dict):
            raise HTTPException(status_code=502, detail="Invalid sunrise/sunset response")

        try:
            sunrise_raw = str(result["sunrise"])
            sunset_raw = str(result["sunset"])
            sunrise_utc = datetime.fromisoformat(sunrise_raw.replace("Z", "+00:00"))
            sunset_utc = datetime.fromisoformat(sunset_raw.replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=502, detail="Invalid sunrise/sunset response")

        berlin_tz = ZoneInfo("Europe/Berlin")
        return sunrise_utc.astimezone(berlin_tz), sunset_utc.astimezone(berlin_tz)

    async def _add_zero_anchors_from_sun_times(
        self,
        parsed_points: list[tuple[datetime, float]],
        latitude: float,
        longitude: float,
    ) -> list[tuple[datetime, float]]:
        if not parsed_points:
            return parsed_points

        point_days = sorted({ts.date() for ts, _ in parsed_points})
        with_anchors = list(parsed_points)

        for day in point_days:
            berlin_tz = ZoneInfo("Europe/Berlin")
            min_sunrise = datetime.combine(day, self.MIN_SUNRISE_TIME, tzinfo=berlin_tz)
            max_sunset = datetime.combine(day, self.MAX_SUNSET_TIME, tzinfo=berlin_tz)

            try:
                sunrise_ts, sunset_ts = await self._fetch_sunrise_sunset_for_day(latitude, longitude, day)
            except HTTPException:
                sunrise_ts = min_sunrise
                sunset_ts = max_sunset

            if sunrise_ts < min_sunrise:
                sunrise_ts = min_sunrise
            if sunset_ts > max_sunset:
                sunset_ts = max_sunset

            if sunrise_ts >= sunset_ts:
                sunrise_ts = min_sunrise
                sunset_ts = max_sunset

            # Always persist hard day bounds so downstream interpolation has fixed zero anchors.
            with_anchors.append((min_sunrise, 0.0))
            with_anchors.append((max_sunset, 0.0))
            with_anchors.append((sunrise_ts, 0.0))
            with_anchors.append((sunset_ts, 0.0))

        return self._merge_points_keep_lowest_energy(with_anchors)

    def _run_has_required_zero_bound_anchors(
        self,
        points: list[PVForecastPoint],
        target_days: list[date],
    ) -> bool:
        point_index: dict[date, set[time]] = {}
        for point in points:
            day = point.ts.date()
            local_time = point.ts.timetz().replace(tzinfo=None)
            point_index.setdefault(day, set()).add(local_time)

        for day in target_days:
            day_times = point_index.get(day, set())
            if self.MIN_SUNRISE_TIME not in day_times or self.MAX_SUNSET_TIME not in day_times:
                return False
        return True

    @staticmethod
    def _to_aware_berlin(ts: datetime | None) -> datetime | None:
        if ts is None:
            return None
        if ts.tzinfo is None:
            return ts.replace(tzinfo=ZoneInfo("Europe/Berlin"))
        return ts.astimezone(ZoneInfo("Europe/Berlin"))

    def _should_refresh_run(
        self,
        pv: Photovoltaik,
        run: PVForecastRun | None,
        target_days: list[date],
    ) -> bool:
        if run is None:
            return True
        if not self._covers_target_days(run.points, target_days):
            return True
        if not self._run_has_required_zero_bound_anchors(run.points, target_days):
            return True

        pv_updated_at = self._to_aware_berlin(getattr(pv, "updated_at", None))
        run_requested_at = self._to_aware_berlin(run.requested_at)
        if pv_updated_at is None or run_requested_at is None:
            return True

        # Re-fetch only when PV config changed after forecast generation.
        return pv_updated_at > run_requested_at

    async def _resolve_user_pv(self, db: AsyncSession, pv_id: Optional[int], pv_owner_id: int) -> Photovoltaik:
        try:
            if pv_id is not None:
                result = await db.execute(
                    select(Photovoltaik).where(
                        and_(Photovoltaik.id == pv_id, Photovoltaik.owner_id == pv_owner_id)
                    )
                )
                pv = result.scalar_one_or_none()
            else:
                result = await db.execute(
                    select(Photovoltaik)
                    .where(Photovoltaik.owner_id == pv_owner_id)
                    .order_by(Photovoltaik.id.asc())
                    .limit(1)
                )
                pv = result.scalar_one_or_none()
        except SQLAlchemyError:
            raise HTTPException(status_code=500, detail="Could not query PV")

        if not pv:
            raise HTTPException(status_code=404, detail="Could not find PV")
        return pv

    async def _create_forecast_for_pv(self, db: AsyncSession, pv: Photovoltaik, pv_owner_id: int):
        lat, lon, dec, az, kwp = pv.get_PV_data()
        forecast, requested_api = await self.fetch_data_api(lat, lon, dec, az, kwp)

        now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
        parsed_points: list[tuple[datetime, float]] = []
        for ts_raw, value in forecast.items():
            ts = datetime.fromisoformat(ts_raw.replace(" ", "T")).replace(
                tzinfo=ZoneInfo("Europe/Berlin")
            )
            parsed_points.append((ts, float(value)))

        parsed_points = await self._add_zero_anchors_from_sun_times(parsed_points, lat, lon)

        target_day = min((ts.date() for ts, _ in parsed_points), default=now_berlin.date())

        try:
            new_run = PVForecastRun(
                pv_id=pv.id,
                pv_owner_id=pv_owner_id,
                requested_api=requested_api,
                requested_at=now_berlin,
                target_day=target_day,
            )
            db.add(new_run)
            await db.flush()

            points = [
                PVForecastPoint(
                    id_run=new_run.run_id,
                    ts=ts,
                    energy_wh=value,
                )
                for ts, value in parsed_points
            ]
            db.add_all(points)

            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Could not create run information")

    async def _latest_run_for_pv(self, db: AsyncSession, pv_id: int, pv_owner_id: int):
        stmt = (
            select(PVForecastRun)
            .options(selectinload(PVForecastRun.points))
            .where(
                PVForecastRun.pv_id == pv_id,
                PVForecastRun.pv_owner_id == pv_owner_id,
            )
            .order_by(PVForecastRun.requested_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def _covers_target_days(self, points: list[PVForecastPoint], target_days: list[date]) -> bool:
        point_days = {p.ts.date() for p in points}
        return all(day in point_days for day in target_days)

    def _serialize_run(self, run: PVForecastRun, target_days: list[date]) -> dict:
        target_set = set(target_days)
        filtered_points = [p for p in run.points if p.ts.date() in target_set]
        filtered_points.sort(key=lambda p: p.ts)


        return {
            "run_id": run.run_id,
            "pv_id": run.pv_id,
            "target_days": target_days,
            "points": [
                {"id_run": p.id_run, "ts": p.ts, "energy_wh": p.energy_wh}
                for p in filtered_points
            ],
            
        } 

    async def get_forecast_for_pv(
        self,
        db: AsyncSession,
        pv_id: Optional[int],
        pv_owner_id: int,
        target_days: Optional[list[date]],
    ):
        target_days = target_days or self._default_target_days()
        pv = await self._resolve_user_pv(db, pv_id, pv_owner_id)

        run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

        if self._should_refresh_run(pv=pv, run=run, target_days=target_days):
            await self._create_forecast_for_pv(db, pv, pv_owner_id)
            run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

        if run is None:
            raise HTTPException(status_code=503, detail="Could not obtain PV data")

        return self._serialize_run(run, target_days)

    async def get_forecast_for_pvs(
        self,
        db: AsyncSession,
        pv_owner_id: int,
        target_days: Optional[list[date]],
    ):
        target_days = target_days or self._default_target_days()

        try:
            result = await db.execute(
                select(Photovoltaik)
                .where(Photovoltaik.owner_id == pv_owner_id)
                .order_by(Photovoltaik.id.asc())
            )
            pvs = result.scalars().all()
        except SQLAlchemyError:
            raise HTTPException(status_code=500, detail="Could not query PV")

        if not pvs:
            raise HTTPException(status_code=404, detail="Could not find PV")

        forecasts: list[dict] = []
        for pv in pvs:
            run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

            if self._should_refresh_run(pv=pv, run=run, target_days=target_days):
                await self._create_forecast_for_pv(db, pv, pv_owner_id)
                run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

            if run is None:
                raise HTTPException(status_code=503, detail=f"Could not obtain PV data for pv_id={pv.id}")

            forecasts.append(self._serialize_run(run, target_days))


        return forecasts


## review api_pvgis_fallback
import asyncio 

async def _run():
    service = PVForecastService()

    dict1=await service._fetch_data_api_pvgis_fallback(51.0,13.7,20,180,3)

    print(dict1)
def main():
    result = asyncio.run(_run())
    print(result)

if __name__ == "__main__":
    main()