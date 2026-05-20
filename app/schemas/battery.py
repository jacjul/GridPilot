from pydantic import BaseModel
from typing import Optional

class BESSCreateform(BaseModel):
    name: Optional[str] = None
    kw_peak_charge: float
    kw_peak_discharge: Optional[float] = None
    kwh: float

class BESSUpdateform(BaseModel):
    name: Optional[str] = None
    kw_peak_charge: Optional[float] = None
    kw_peak_discharge: Optional[float] = None
    kwh: Optional[float] = None


