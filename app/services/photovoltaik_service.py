from sqlalchemy import select, and_, update, delete
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
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
    GEOCODE_URL = "https://nominatim.openstreetmap.org/search"

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

    async def fetch_data_api(self, latitude, longitude, declination, azimuth, kwp):
        url = f"{self.BASE_URL}/{latitude}/{longitude}/{declination}/{azimuth}/{kwp}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError:
                raise HTTPException(status_code=502, detail="Forecast provider returned an error")
            except httpx.RequestError:
                raise HTTPException(status_code=503, detail="Forecast provider unreachable")

            result = payload.get("result")
            if isinstance(result, list):
                return result[0] if result else {}
            if isinstance(result, dict):
                return result
            raise HTTPException(status_code=502, detail="Unexpected forecast response")

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
        forecast = await self.fetch_data_api(lat, lon, dec, az, kwp)

        now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
        parsed_points: list[tuple[datetime, float]] = []
        for ts_raw, value in forecast.items():
            ts = datetime.fromisoformat(ts_raw.replace(" ", "T")).replace(
                tzinfo=ZoneInfo("Europe/Berlin")
            )
            parsed_points.append((ts, value))

        target_day = min((ts.date() for ts, _ in parsed_points), default=now_berlin.date())

        try:
            new_run = PVForecastRun(
                pv_id=pv.id,
                pv_owner_id=pv_owner_id,
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

        if run is None or not self._covers_target_days(run.points, target_days):
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

            if run is None or not self._covers_target_days(run.points, target_days):
                await self._create_forecast_for_pv(db, pv, pv_owner_id)
                run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

            if run is None:
                raise HTTPException(status_code=503, detail=f"Could not obtain PV data for pv_id={pv.id}")

            forecasts.append(self._serialize_run(run, target_days))


        return forecasts
