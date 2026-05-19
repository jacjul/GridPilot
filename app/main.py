from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router_v1
from app.db.database import Base, async_engine

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


app = FastAPI()
app.include_router(router_v1)


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