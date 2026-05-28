from app.core.celery import celery
from celery.schedules import crontab
from app.core.settings import settings
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.db.database import engine
import asyncio
import app.models
from app.services.electricity_service import ElectricityService
from app.services.photovoltaik_service import PVForecastService
from app.models.photovoltaik import Photovoltaik



SessionCelery = sessionmaker(bind=engine,expire_on_commit=False)



celery.conf.beat_schedule= {
    "worker_for_fetching_EPEX_data":{
       "task": "task.fetch_EPEX_data",
       "schedule" :crontab(minute="*/36")
    }
}

@celery.task(name="task.fetch_EPEX_data")
def fetch_EPEX_data():
    
    with SessionCelery() as session:
        elec_service = ElectricityService()

        response = elec_service.fetch_EPEX_API_for_worker(session)

    return response
    

@celery.task(name="task.create_monthly_PV_profiles", bind=True, acks_late=True)
def create_monthly_PV_profiles(self, pv_id: int):

    with SessionCelery() as session:

        pv = session.execute(select(Photovoltaik).where(Photovoltaik.id==pv_id)).scalar_one_or_none()
        if pv is None:
            return {"status": "not_found", "pv_id": pv_id}
        pv_service= PVForecastService()

        df_monthly = pv_service._fetch_data_api_pvgis_fallback_new(pv.latitude,pv.longitude,pv.declination,pv.azimuth,pv.kw_peak)
        t = pv_service._upsert_monthly_profiles(db=session, pv_id=pv_id, df = df_monthly)

    return t 
