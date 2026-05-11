from pydantic import BaseModel
from typing import Optional
from datetime import date, time

class EVform(BaseModel):
    ev_name:Optional[str]
    kw_peak_loading:float
    kwh_battery:float


class EVDowntimeRuleCreate(BaseModel):
    ev_id :int 
    weekdays_mask: int
    start_time: time
    end_time: time
    valid_from: date | None = None
    valid_to: date | None = None
    tz_name: str = "Europe/Berlin"

class EVDowntimeRuleUpdate(BaseModel):
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