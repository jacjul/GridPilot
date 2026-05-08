from sqlalchemy import select, and_
from fastapi import HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional 
from zoneinfo import ZoneInfo
from sqlalchemy.exc import SQLAlchemyError

from app.models.photovoltaik import Photovoltaik
from app.models.PV_forecast import PVForecastRun,PVForecastPoint
from app.schemas.user import UserMe
from app.schemas.photovoltaik import PVform

class PVForecastService:
    BASE_URL = "https://api.forecast.solar/estimate/watthours"

    async def create_new_PV(self,formdata:PVform,user:UserMe, db:AsyncSession):
        new_pv = Photovoltaik(latitude=formdata.latitude,
                            longitude=formdata.longitude,
                            declination=formdata.declination,
                            azimuth=formdata.azimuth,
                            kw_peak=formdata.kw_peak,
                            owner_id =user.id)

        try:
            db.add(new_pv)
            await db.commit()
            await db.refresh(new_pv)
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not add the PV")
        return {"message": "success"}

    async def fetch_data_api(self, latitude, longitude,declination,azimuth,kwp) :

        url = f"{self.BASE_URL}/{latitude}/{longitude}/{declination}/{azimuth}/{kwp}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            result = payload.get("result")
            if isinstance(result,list):
                return result[0] if result else {}
            if isinstance(result,dict):
                return result
            raise HTTPException(status_code=502,detail="Unexpected forecast repsonse")
        
        """{
  "result": [
    {
      "2000-01-01 08:00": 12.345,
      "2000-01-01 09:00": 35.801
    }
  ],
  "message": {
    "code": 0,
    "type": "success",
    "text": ""
  }
}"""
        
    async def get_forecast_for_pv(self, db:AsyncSession, pv_id:Optional[int], pv_owner_id:int):
        if pv_id:
            try:
                result = await db.execute(select(Photovoltaik).where(and_(Photovoltaik.id ==pv_id, Photovoltaik.owner_id==pv_owner_id)))
                pv = result.scalar_one_or_none()

            except:
                raise HTTPException(status_code=500, detail="Couldnt find pv_id")
        else:
            try:
                result = await db.execute(select(Photovoltaik).where(Photovoltaik.owner_id==pv_owner_id))
                pv = result.scalars().first() # this still just get the first PV not all 
            except:
                raise HTTPException(status_code=500, detail="Couldnt find PV to the user_id")


        # this will only search the first PV for a user not all
        # for now sufficient but this has to be changed 
        
        if not pv:
            raise HTTPException(status_code=404, detail="Could not find PV")
        

        lat,lon,dec,az,kwp = pv.get_PV_data()

        forecast = await self.fetch_data_api(lat,lon,dec,az,kwp )

        now_berlin =datetime.now(ZoneInfo("Europe/Berlin"))
        try:
            new_run = PVForecastRun(
                pv_id = pv.id,
                requested_at = now_berlin,
                target_day = now_berlin.date()
            )
            db.add(new_run)
            await db.flush()
            points  = []
            for ts_raw,value in forecast.items():
                ts = datetime.fromisoformat(ts_raw.replace(" ", "T")).replace(tzinfo=ZoneInfo("Europe/Berlin"))

                new_point =  PVForecastPoint(id_run=new_run.run_id,
                                            ts = ts ,
                                            energy_wh = value)# how to add the id of PVForecast
                points.append(new_point)

            
            db.add_all(points)

            await db.commit()
        except:
            await db.rollback()
            raise HTTPException(status_code=409, detail ="Coulnt create Run-Information")
 
        return {"run_id": new_run.run_id, "points_count": len(points)}

        