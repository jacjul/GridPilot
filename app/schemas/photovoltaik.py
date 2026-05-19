from pydantic import BaseModel,ConfigDict

class PVform(BaseModel):
    place:str
    declination:float
    azimuth:float
    kw_peak:float
    einspeiseverguetung:float

class PVUpdateForm(BaseModel):
    place: str | None = None
    declination: float | None = None
    azimuth: float | None = None
    kw_peak: float | None = None
    einspeiseverguetung: float | None = None

class PVOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  

    id: int
    latitude: float
    longitude: float
    declination: float
    azimuth: float
    kw_peak: float
    einspeiseverguetung: float