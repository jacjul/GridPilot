from fastapi import FastAPI

from app.api.v1.router import router_v1

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