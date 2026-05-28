from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer,Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.photovoltaik import Photovoltaik
    from app.models.user import User


class PVForecastRun(Base):
    __tablename__ = "pv_forecast"

    run_id:Mapped[int] = mapped_column(primary_key = True)
    pv_id:Mapped[int] =mapped_column (ForeignKey("photovoltaik.id" , ondelete="CASCADE"))
    pv_owner_id:Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    requested_api:Mapped[str] = mapped_column(default="forecast.solar")
    requested_at:Mapped[datetime] = mapped_column(DateTime(timezone=True))
    target_day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status:Mapped[str] = mapped_column(default = "ok")

    pv:Mapped["Photovoltaik"] = relationship("Photovoltaik" , back_populates="forecasts")

    points:Mapped[list["PVForecastPoint"]] = relationship("PVForecastPoint", back_populates="run", cascade="all, delete-orphan",passive_deletes=True)

class PVForecastPoint(Base):
    __tablename__ = "pv_forecast_point"

    id_run:Mapped[int] = mapped_column(ForeignKey("pv_forecast.run_id", ondelete="CASCADE"), primary_key=True)
    ts :Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True )
    energy_wh:Mapped[float] = mapped_column(Float, nullable=False)

    run:Mapped["PVForecastRun"] = relationship("PVForecastRun", back_populates="points")

class PVMonthlyProfileFallback(Base):
    __tablename__ = "pv_monthly_profile_fallback"
    #__table_args__=(Index("ix_pv_monthly_pv_id", "pv_id"),)

    pv_id:Mapped[int] = mapped_column(ForeignKey("photovoltaik.id",ondelete="CASCADE"), primary_key =True,index=True)
    month:Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    hour:Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    energy_wh_avg:Mapped[float] = mapped_column(Float, nullable=False)
    computed_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
