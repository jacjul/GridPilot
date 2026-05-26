from celery import Celery
from celery.schedules import crontab
from app.core.settings import settings
from redis.asyncio import Redis 
from sqlalchemy.orm import sessionmaker
from app.db.database import engine
import asyncio
import app.models
from app.services.electricity_service import ElectricityService
import app.models

r_celery = Redis.from_url(settings.REDIS_URL_CELERY, decode_responses=True)


SessionCelery = sessionmaker(bind=engine,expire_on_commit=False)


celery = Celery("worker", broker=settings.REDIS_URL_CELERY, backend=settings.REDIS_URL_CELERY)

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
    
    




