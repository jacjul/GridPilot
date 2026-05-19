from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import Optional 
from datetime import datetime
from app.models.price_electricity import MarketZone,PriceTyp


class ElectricityCreateform (BaseModel):

    price_typ: PriceTyp
    fixed_price: Optional[float] = None
    market_zone: Optional[MarketZone] = None
    name: Optional[str] = None

class ElectricityUpdateForm(BaseModel):
    price_typ: Optional[PriceTyp] = None
    fixed_price: Optional[float] = None
    market_zone: Optional[MarketZone] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None

class ElectricityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    price_typ: PriceTyp
    fixed_price: Optional[float]
    market_zone: MarketZone
    is_active: bool

class DynamicPricePointsOut(BaseModel):
    
    marketzone:MarketZone
    timestamp:datetime
    price:float

class DynamicPricePointsGet(BaseModel):
    timestamps:list[datetime]
    prices: list[float]