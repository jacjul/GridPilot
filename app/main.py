from fastapi import FastAPI

from app.api.v1.router import router_v1

# Import endpoint modules so decorators register routes on router_v1.
from app.api.v1 import auth  # noqa: F401
from app.api.v1 import user  # noqa: F401


app = FastAPI()
app.include_router(router_v1)