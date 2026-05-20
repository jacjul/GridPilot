from pydantic import BaseModel
from typing import Optional
from datetime import date, time

class EVform(BaseModel):
    ev_name:Optional[str]
    kw_peak_loading:float
    kwh_battery:float

class EVUpdateForm(BaseModel):
    ev_name: Optional[str] = None
    kw_peak_loading: Optional[float] = None
    kwh_battery: Optional[float] = None


class EVDowntimeRuleCreate(BaseModel):
    ev_id :int 
    weekdays_mask: int
    start_time: time
    end_time: time
    valid_from: date | None = None
    valid_to: date | None = None
    soc_target_start_pct: float | None = None
    soc_target_end_pct: float | None = None
    tz_name: str = "Europe/Berlin"

class EVDowntimeRuleUpdate(BaseModel):
    weekdays_mask: int
    start_time: time
    end_time: time
    valid_from: date | None = None
    valid_to: date | None = None
    soc_target_start_pct: float | None = None
    soc_target_end_pct: float | None = None
    tz_name: str = "Europe/Berlin"


class EVDowntimeRuleOut(BaseModel):
    id: int
    ev_id: int
    weekdays_mask: int
    start_time: time
    end_time: time
    valid_from: date | None = None
    valid_to: date | None = None
    soc_target_start_pct: float | None = None
    soc_target_end_pct: float | None = None
    tz_name: str


class EVDowntimeExceptionCreate(BaseModel):
    day: date
    start_time: time
    end_time: time