from redis.asyncio import Redis 
from app.core.settings import settings
from celery import Celery
r_celery = Redis.from_url(settings.REDIS_URL_CELERY, decode_responses=True)

celery = Celery("worker", broker=settings.REDIS_URL_CELERY, backend=settings.REDIS_URL_CELERY)
