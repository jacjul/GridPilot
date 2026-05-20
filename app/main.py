from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
import time
import uuid 

from app.api.v1.router import router_v1
from app.db.database import Base, async_engine
from app.core.settings import settings
# Ensure all ORM models are imported so SQLAlchemy metadata is populated.
from app.models import battery  # noqa: F401
from app.models import electric_vehicle  # noqa: F401
from app.models import optimization  # noqa: F401
from app.models import photovoltaik  # noqa: F401
from app.models import price_electricity  # noqa: F401
from app.models import PV_forecast  # noqa: F401
from app.models import token  # noqa: F401
from app.models import user  # noqa: F401

# Import endpoint modules so decorators register routes on router_v1.
from app.api.v1 import auth  # noqa: F401
from app.api.v1 import user  # noqa: F401
from app.api.v1 import battery
from app.api.v1 import electric_vehicle
from app.api.v1 import electricity
from app.api.v1 import photovoltaik
from app.api.v1 import optimization
from app.api.v1 import health

from app.logger import logger,setup_logging

app = FastAPI()
app.include_router(router_v1)











@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "request_id": request_id,
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.exception(
        "unhandled exception",
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Unexpected server error",
                "request_id": request_id,
            }
        },
    )

if settings.ENV == "DEV":
    @app.on_event("startup")
    async def create_tables_on_startup() -> None:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)



origins=["localhost:5173","localhost"]

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_headers= ["*"], 
    allow_methods=["*"],
    allow_credentials=True
)

setup_logging(settings.LOG_LEVEL)
@app.middleware("http")
async def create_general_logging(request:Request, call_next):

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as e:
        duration_ms = round((time.perf_counter()-start_time)*1000,2)
        logger.exception("request failed after %sms %s %s",
                         duration_ms,
                         request.method,
                         request.url.path,
                           extra={"request_id":request_id})
        raise
    duration_ms = round((time.perf_counter()-start_time) *1000,2)

    logger.info(msg=f"{request.method} - {request.url.path} - {response.status_code} -{duration_ms}",
                extra={"request_id":request_id})
    
    response.headers["X-Request-ID"] = request_id

    return response 