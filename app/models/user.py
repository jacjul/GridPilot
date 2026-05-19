from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy import String
from typing import TYPE_CHECKING

from app.db.database import Base
if TYPE_CHECKING:
    from app.models.photovoltaik import Photovoltaik
    from app.models.electric_vehicle import ElectricVehicle
    from app.models.battery import Battery
    from app.models.price_electricity import ElectricityPrice
    from app.models.token import Token



class User(Base):
    __tablename__ ="users"

    id:Mapped[int] = mapped_column(primary_key =True)
    name:Mapped[str] =mapped_column(String(50))
    lastname: Mapped[str] =mapped_column(String(50))
    username: Mapped[str] =mapped_column(String(70), unique=True,nullable=False, index=True)
    email: Mapped[str] =mapped_column(String(70), unique=True,nullable=False, index=True)
    hashed_password:Mapped[str] 
    photovoltaik_owned:Mapped[list["Photovoltaik"]] = relationship(
        "Photovoltaik", back_populates="owner", cascade="all, delete-orphan",
        passive_deletes=True)
    electric_vehicle_owned:Mapped[list["ElectricVehicle"]] = relationship("ElectricVehicle", back_populates="owner", cascade="all, delete-orphan",passive_deletes=True)
    battery_owned:Mapped[list["Battery"]] = relationship("Battery", back_populates="owner", cascade="all, delete-orphan",passive_deletes=True)
    electricity_owned:Mapped[list["ElectricityPrice"]] = relationship("ElectricityPrice", back_populates="owner", cascade="all, delete-orphan",passive_deletes=True)

    refresh_tokens:Mapped[list["Token"]] = relationship("Token", back_populates="user", cascade="all, delete-orphan")