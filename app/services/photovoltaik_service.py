from sqlalchemy import select, and_, update, delete
from sqlalchemy.orm import selectinload,Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from fastapi import HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta, time
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy.exc import SQLAlchemyError,IntegrityError
import pandas as pd 
from suntime import Sun
import seaborn as sns
import matplotlib.pyplot as plt 
from app.logger import logger 
from app.models.photovoltaik import Photovoltaik
from app.models.PV_forecast import PVForecastRun, PVForecastPoint,PVMonthlyProfileFallback
from app.schemas.user import UserMe
from app.schemas.photovoltaik import PVform,PVOut,PVUpdateForm
from app.core.celery import celery

class PVForecastService:
    BASE_URL = "https://api.forecast.solar/estimate/watthours/period"
    ## https://re.jrc.ec.europa.eu/api/seriescalc?lat=45&lon=8&outputformat=json&startyear=2022&endyear=2023&pvcalculation=1&peakpower=10&loss=14
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

    def _default_target_sunrise_sunset(self,latitude,longitude, safety_hours=1) -> list[datetime]:
        today_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
        tomorrow_berlin = today_berlin +timedelta(days=1)

        sun = Sun(latitude,longitude)
        # deltas for safety
        sunrise_today:datetime = sun.get_sunrise_time(today_berlin) +timedelta(hours=safety_hours)
        sunset_tomorrow:datetime = sun.get_sunset_time(tomorrow_berlin)-timedelta(hours=-safety_hours)
        return [sunrise_today, sunset_tomorrow]

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
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="IntegrityError occured when creating PV")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not add the PV")
        
        #this should be done through celery background worker 
        celery.send_task("task.create_monthly_PV_profiles", args=[new_pv.id])
        """
        df_create  = await self._fetch_data_api_pvgis_fallback_new(new_pv.latitude,
                                                new_pv.longitude,
                                                new_pv.declination,
                                                new_pv.azimuth,
                                                new_pv.kw_peak)
        
        await self._upsert_monthly_profiles(db=db, pv_id=new_pv.id, df = df_create)
        """
        return {"message": "success", "latitude": latitude, "longitude": longitude}

    def _upsert_monthly_profiles(self,db:Session, pv_id:int, df:pd.DataFrame):
        created_at = datetime.now(ZoneInfo("Europe/Berlin"))
        records = (df.reset_index(drop=True)
                   .assign(pv_id=pv_id, computed_at=created_at)
                   .loc[:,["pv_id","computed_at","month","hour","energy_wh_avg"]]
                   .to_dict(orient="records"))
        
        if not records:
            return
        
        stmt = pg_insert(PVMonthlyProfileFallback).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["pv_id","hour","month"],
            set_={
                "energy_wh_avg": stmt.excluded.energy_wh_avg,
                "computed_at": stmt.excluded.computed_at,
            }
        )
        db.execute(stmt)
        db.commit()
        return {"message":"success"}
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

    async def _fetch_data_api_forecast_solar(self, latitude, longitude, declination, azimuth, kwp)->dict[str,float]:
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
        raise HTTPException(status_code = 503, detail = "Unexpected forecast.solar response")

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
    def _fetch_data_api_pvgis_fallback_new(self, latitude, longitude, declination, azimuth, kwp):
        now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))

        with httpx.Client(timeout=15.0) as client:
            
            pvgis_params = {
                    "lat": latitude,
                    "lon": longitude,
                    "startyear": 2019,
                    "endyear": 2020,
                    "pvcalculation": 1,
                    "peakpower": kwp,
                    "loss": 14,
                    "angle": declination,
                    "aspect": azimuth,
                    "outputformat": "json",
                }

            try:
                response = client.get(self.PVGIS_URL, params=pvgis_params)
                response.raise_for_status()
                payload = response.json()
                
            
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.exception(f"Following error occured {exc}")
                raise HTTPException(status_code=503,detail="Something went wrong when fetching PVGIS data")

            output = payload.get("outputs", {})
            hourly = output.get("hourly")

            if not isinstance(hourly,list) or not hourly:
                logger.info(f"This is hourly: {hourly} - its not a list")
                raise HTTPException(status_code=503, detail="List Output wrong")
            
            times = []
            watts_avg =[]
            for rows in hourly:
                if not isinstance(rows,dict) or not rows:
                    logger.exception(f"rows are not a dict")
                    raise HTTPException(status_code=400, detail = "rows are in wrong format")

            
                time_str = rows["time"]
                if  not isinstance(time_str,str):
                    continue
                time_datetime = datetime.strptime(time_str,"%Y%m%d:%H%M") 
                #time_datetime_tz = time_datetime.replace(tzinfo=ZoneInfo("Europe/Berlin"))
                times.append(time_datetime)

                watt_float = float(rows["P"])
                if not isinstance(watt_float,float):
                    continue
                watts_avg.append(watt_float)

            df_val = pd.DataFrame({
                "times" : times, "energy_wh_avg": watts_avg
            })

            if df_val.empty:
                logger.error("df is empty")
                
            df_monthly = self.create_representative_monthly_df(df_val,debug=False)
            return df_monthly

    def create_representative_monthly_df(self, df:pd.DataFrame, debug:bool)->pd.DataFrame:
            df["month"] = df["times"].dt.month
            df["hour"] = df["times"].dt.hour 

            df_grouped = df.groupby([df["month"], df["hour"]])["energy_wh_avg"].mean()
            if debug:
                from pathlib import Path
                csv_path = Path(__file__).resolve().parents[2] /"pv_monthly.csv"
                df_grouped.reset_index().to_csv(csv_path)

                pivot = df_grouped.reset_index().pivot(index="month", columns="hour", values="watts")
                sns.heatmap(pivot, cmap="viridis")
                png_path = Path(__file__).resolve().parents[2] / "pv_monthly_heatmap.png"
                plt.savefig(png_path, dpi =150)
            return df_grouped.reset_index()
            
    ###_fetch_data_api_pvgis_fallback this is outdated and was used during real time, now initial celery job when creating PV
    async def _fetch_data_api_pvgis_fallback(self, latitude, longitude, declination, azimuth, kwp):
        now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
        candidate_years = [
            now_berlin.year - 1,
            now_berlin.year - 2,
            now_berlin.year - 3,

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
                raise HTTPException(status_code=503, detail=f"Unexpected PVGIS response")


        outputs = payload.get("outputs", {})
        hourly = outputs.get("hourly")
        if not isinstance(hourly, list) or not hourly:
            raise HTTPException(status_code=503, detail=f"Unexpected PVGIS response")

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
            raise HTTPException(status_code=503, detail="PVGIS fallback had no usable hourly values")

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
            raise HTTPException(status_code=503, detail=f"Unexpected PVGIS response")

        return result

    async def fetch_data_api(self, latitude, longitude, declination, azimuth, kwp,pv_id,db) -> tuple[dict[str, float], str]:
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
            month_today = datetime.now(tz=ZoneInfo("Europe/Berlin")).month

            result = await db.execute(select(PVMonthlyProfileFallback).where(PVMonthlyProfileFallback.pv_id==pv_id,
                                                                             PVMonthlyProfileFallback.month==month_today))
            rows = result.mappings().all()
            if not rows:
                raise HTTPException(status_code=500, detail="Could not get PVGIS-fallback data for pv")
            forecast:dict[str,float]= {}
            date_now = datetime.now()
            for idx,row in enumerate(rows):
                energy = row.get("energy_wh_avg", 0.0)
                hour = row.get("hour",None)
                if idx <24:
                    datetime_t = date_now.replace(hour=hour, minute=0,second=0)
                else:
                    datetime_t = date_now.replace(hour=hour, minute=0,second=0) +timedelta(days=1)
                datetime_t = datetime_t.strftime("%Y-%m-%d %H:%M:%S")
                forecast[datetime_t] =energy
            return forecast, "pvgis_fallback"
        except:
            raise HTTPException(status_code=500, detail="Could not get PVGIS-fallback data for pv")



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
                sunrise_ts, sunset_ts = self._default_target_sunrise_sunset(latitude, longitude, 0)
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
        start_sunrise: datetime,
        end_sunset:datetime
    ) -> bool:
        if run is None:
            return True
        if not self._covers_target_days(run.points, start_sunrise, end_sunset):
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
        forecast, requested_api = await self.fetch_data_api(lat, lon, dec, az, kwp,pv.id,db)
        logger.info(f"{forecast}")
        now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
        parsed_points: list[tuple[datetime, float]] = []
        for ts_raw, value in forecast.items():
            ts = datetime.fromisoformat(ts_raw.replace(" ", "T")).replace(
                tzinfo=ZoneInfo("Europe/Berlin")
            )
            parsed_points.append((ts, float(value)))

        #parsed_points = await self._add_zero_anchors_from_sun_times(parsed_points, lat, lon)

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

    def _covers_target_days(self, points: list[PVForecastPoint], start_sunrise: datetime, end_sunset:datetime) -> bool:
        point_daytimes:set[datetime] = {p.ts for p in points}
        if not point_daytimes:
            return False
        if start_sunrise> min(point_daytimes) and end_sunset< max(point_daytimes):
            return True
        return False
        
        

    def _serialize_run(self, run: PVForecastRun, start_time:datetime, end_time:datetime) -> dict:
        filtered_points = [p for p in run.points if p.ts > start_time and p.ts < end_time]
        filtered_points.sort(key=lambda p: p.ts)


        return {
            "run_id": run.run_id,
            "pv_id": run.pv_id,
            "target_days": [start_time, end_time],
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
        
    ):
        pv = await self._resolve_user_pv(db, pv_id, pv_owner_id)

        start_sunrise,end_sunset =self._default_target_sunrise_sunset(pv.latitude,pv.longitude)

        run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

        if self._should_refresh_run(pv=pv, run=run, start_sunrise=start_sunrise, end_sunset=end_sunset):
            await self._create_forecast_for_pv(db, pv, pv_owner_id)
            run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

        if run is None:
            raise HTTPException(status_code=503, detail="Could not obtain PV data")

        return self._serialize_run(run, start_sunrise,end_sunset)

    async def get_forecast_for_pvs(
        self,
        db: AsyncSession,
        pv_owner_id: int,
    ):
        
        # 1. get target days today and tomorrow date
        # 2. get scalars for all PVs that are owned by user
        # 3. iterate through pvs -> per PV
            # 4. searches latest run with PVForecastRun and does load PVForecastPoints
            # 5. check if should rerun with _should_refresh_run 

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

        start_sunrise,end_sunset = self._default_target_sunrise_sunset(pvs[0].latitude,pvs[0].longitude)

        for pv in pvs:
            

            run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

            if self._should_refresh_run(pv=pv, run=run, start_sunrise=start_sunrise,end_sunset=end_sunset):
                logger.info("der RUN musste zweimal durchgeführt werden")
                await self._create_forecast_for_pv(db, pv, pv_owner_id)
                run = await self._latest_run_for_pv(db, pv.id, pv_owner_id)

            if run is None:
                raise HTTPException(status_code=503, detail=f"Could not obtain PV data for pv_id={pv.id}")

            forecasts.append(self._serialize_run(run, start_sunrise,end_sunset))


        return forecasts


## review api_pvgis_fallback
import asyncio 

async def _run():

    service = PVForecastService()

    df1=await service._fetch_data_api_pvgis_fallback_new(52.2,13.7,20,180,10)
    logger.info(f"{df1}")
def main():
    asyncio.run(_run())
    

if __name__ == "__main__":
    from app.logger import setup_logging
    from app.core.settings import settings
    setup_logging(settings.LOG_LEVEL)
    main()