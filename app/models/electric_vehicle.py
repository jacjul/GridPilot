from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy import Float,ForeignKey
from typing import TYPE_CHECKING

from app.db.database import Base
if TYPE_CHECKING:
    from app.models.user import User

class ElectricVehicle(Base):
    __tablename__ = "electric_vehicle"

    id:Mapped[int] = mapped_column(primary_key=True)
    ev_name:Mapped[str] = mapped_column(nullable=True)
    kw_peak_loading:Mapped[float] = mapped_column(Float , nullable=False)
    kwh_battery:Mapped[float]= mapped_column(Float, nullable=False) 
    owner_id:Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner:Mapped["User"] = relationship("User", back_populates="electric_vehicle_owned")
