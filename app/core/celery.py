from celery import Celery
from celery.schedules import crontab
from app.core.settings import settings
from redis.asyncio import Redis 
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.db.database import AsyncSessionLocal

from app.services.electricity_service import ElectricityService

r_celery = Redis.from_url(settings.REDIS_URL_CELERY, decode_responses=True)

celery = Celery("get_EPEX_data",broker =settings.REDIS_URL_CELERY, backend=settings.REDIS_URL_CELERY)


celery.conf.beat_schedule = {
    "load_API_once_every_30_minutes":{
        "task":"tasks.call_EPEX_api",
        "schedule": crontab(minute="*/30")
    }
}

@celery.task(name="tasks.call_EPEX_api")
def call_EPEX_api():
    import asyncio
    async def run():
        async with AsyncSessionLocal() as session:
            elec_service = ElectricityService()
            try:
                response = await elec_service.fetch_EPEX_API_for_worker(session)
            except Exception as e:
                return {"error":str(e)}
        return response 
     
    return asyncio.run(run())