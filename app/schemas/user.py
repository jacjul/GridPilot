from typing import Literal
from pydantic import BaseModel


LoadProfileType = Literal["SLP", "SLP_HEATPUMP"]

class UserRegistration(BaseModel):
    name:str
    lastname: str
    username: str
    email: str
    password:str


class UserMe(BaseModel):
    id: int
    name: str
    lastname: str
    username: str
    email: str
    annual_consumption_kwh: float
    load_profile_type: LoadProfileType


class UserConsumptionUpdate(BaseModel):
    annual_consumption_kwh: float
    load_profile_type: LoadProfileType
