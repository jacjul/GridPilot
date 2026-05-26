from sqlalchemy.orm import Mapped, mapped_column ,relationship
from sqlalchemy import DateTime, Float, ForeignKey,UniqueConstraint
from enum import Enum 
from datetime import datetime 

from typing import TYPE_CHECKING
from app.db.database import Base

if TYPE_CHECKING:
    from app.models.user import User

class PriceTyp(str,Enum):
    fixed = "fixed"
    dynamic_EPEX= "dynamic_EPEX" 

class MarketZone(str,Enum):
    AT = "AT" #(Austria)
    BE = "BE" #(Belgium)
    CH = "CH" #(Switzerland)
    CZ = "CZ" #(Czech Republic)
    DE_LU = "DE-LU" #(Germany, Luxembourg)
    DE_AT_LU = "DE-AT-LU" #(Germany, Austria, Luxembourg)
    DK1 = "DK1" #(Denmark 1)
    DK2 = "DK2" #(Denmark 2)
    FR = "FR" #(France)
    HU = "HU" #(Hungary)
    IT_North = "IT-North" #(Italy North)
    NL = "NL" #(Netherlands)
    NO2 = "NO2" #(Norway 2)
    PL = "PL"#(Poland)
    SE4 = "SE4" #(Sweden 4)
    SI = "SI" # (Slovenia) 
    



class ElectricityPrice(Base):

    __tablename__ = "electricity_price"

    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_owner_name"),)

    id:Mapped[int] = mapped_column(primary_key=True)
    owner_id:Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name:Mapped[str] 
    price_typ:Mapped[PriceTyp] = mapped_column(nullable=False)
    fixed_price:Mapped[float] = mapped_column(Float, nullable=True)
    market_zone:Mapped[MarketZone] = mapped_column(default=MarketZone.DE_LU)
    is_active:Mapped[bool]
    updated_at:Mapped[datetime]

    owner:Mapped["User"] = relationship("User", back_populates="electricity_owned")


class DynamicPricePoints(Base):
    __tablename__ ="dynamic_price_points"

    market_zone:Mapped[MarketZone] = mapped_column(default=MarketZone.DE_LU, primary_key=True)
    timestamp:Mapped[datetime] =mapped_column(DateTime(timezone=True), primary_key=True)
    price:Mapped[float] = mapped_column(Float)

# https://api.energy-charts.info/#/prices/day_ahead_price_price_get  
# https://api.energy-charts.info/price?bzn=DE-LU get day-ahead for germany luxemburg
