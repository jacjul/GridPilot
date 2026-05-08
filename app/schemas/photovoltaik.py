from pydantic import BaseModel

class PVform(BaseModel):
    latitude:float
    longitude:float
    declination:float
    azimuth:float
    kw_peak:float