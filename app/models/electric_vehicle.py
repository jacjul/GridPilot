from __future__ import annotations

from datetime import date, time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Date, Float, ForeignKey, Integer, String, Time
from typing import TYPE_CHECKING

from app.db.database import Base
if TYPE_CHECKING:
    from app.models.user import User

class ElectricVehicle(Base):
    __tablename__ = "electric_vehicle"

    id: Mapped[int] = mapped_column(primary_key=True)
    ev_name: Mapped[str] = mapped_column(nullable=True)
    kw_peak_loading: Mapped[float] = mapped_column(Float, nullable=False)
    kwh_battery: Mapped[float] = mapped_column(Float, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner: Mapped["User"] = relationship("User", back_populates="electric_vehicle_owned")

    downtime_rules: Mapped[list["EVDowntimeRule"]] = relationship(
        "EVDowntimeRule",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    downtime_exceptions: Mapped[list["EVDowntimeException"]] = relationship(
        "EVDowntimeException",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EVDowntimeRule(Base):
    __tablename__ = "ev_downtime_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ev_id: Mapped[int] = mapped_column(ForeignKey("electric_vehicle.id", ondelete="CASCADE"), nullable=False, index=True)
    weekdays_mask: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    soc_target_start_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    soc_target_end_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    tz_name: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Berlin")

    vehicle: Mapped["ElectricVehicle"] = relationship("ElectricVehicle", back_populates="downtime_rules")

    def is_active_weekday(self, weekday: int) -> bool:
        """Weekday uses Python convention: Monday=0 ... Sunday=6."""
        return bool(self.weekdays_mask & (1 << weekday))


class EVDowntimeException(Base):
    __tablename__ = "ev_downtime_exception"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ev_id: Mapped[int] = mapped_column(ForeignKey("electric_vehicle.id", ondelete="CASCADE"), nullable=False, index=True)
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    vehicle: Mapped["ElectricVehicle"] = relationship("ElectricVehicle", back_populates="downtime_exceptions")
