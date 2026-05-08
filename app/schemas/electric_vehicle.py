from pydantic import BaseModel
from typing import Optional
from datetime import date, time

class EVform(BaseModel):
    ev_name:Optional[str]
    kw_peak_loading:float
    kwh_battery:float
    owner_id:int


class EVDowntimeRuleCreate(BaseModel):
    weekdays_mask: int
    start_time: time
    end_time: time
    valid_from: date | None = None
    valid_to: date | None = None
    tz_name: str = "Europe/Berlin"


class EVDowntimeExceptionCreate(BaseModel):
    day: date
    start_time: time
    end_time: time