from sqlalchemy.orm import Mapped, mapped_column ,relationship
from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from typing import TYPE_CHECKING
from datetime import datetime 

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ElectricityPrice(Base):

    __tablename__ = "electricity_price"
    date:Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    user_id:Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    timestamps:Mapped[list[datetime]] = mapped_column(ARRAY(DateTime(timezone=True)), nullable=False)
    price:Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    
    owner:Mapped["User"] = relationship("User", back_populates="electricity_owned")
