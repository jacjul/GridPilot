from sqlalchemy.orm import Mapped, mapped_column ,relationship
from sqlalchemy import ForeignKey,Integer, Float
from typing import TYPE_CHECKING


from app.db.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.PV_forecast import PVForecastRun
#api call free
# https://api.forecast.solar/estimate/:lat/:lon/:dec/:az/:kwp 
# https://api.forecast.solar/estimate/watthours/52.2/12.2/37.4/1.2/5.67
class Photovoltaik(Base):

    __tablename__ = "photovoltaik"

    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    latitude:Mapped[float] = mapped_column(Float ,nullable=False)
    longitude:Mapped[float]= mapped_column(Float ,nullable=False)
    declination:Mapped[float]= mapped_column(Float ,nullable=False)
    azimuth:Mapped[float]= mapped_column(Float ,nullable=False)
    kw_peak:Mapped[float]= mapped_column(Float ,nullable=False)
    
    owner_id:Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),nullable=False, index=True)
    owner:Mapped["User"] = relationship("User", back_populates="photovoltaik_owned")

    forecasts:Mapped[list["PVForecastRun"]] = relationship("PVForecastRun", back_populates="pv" ,
                                                            cascade="all, delete-orphan", passive_deletes=True)

    def get_PV_data(self)->tuple[float,float,float,float,float]:
        return self.latitude, self.longitude, self.declination,self.azimuth,self.kw_peak




