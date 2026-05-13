from pydantic import BaseModel
from enum import Enum
from typing import Optional 
from app.models.price_electricity import MarketZone,PriceTyp


class ElectricityCreateform (BaseModel):

    price_typ:PriceTyp
    fixed_price:Optional[float]
    market_zone:Optional[MarketZone]
    name:Optional[str]

