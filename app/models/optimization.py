from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class OptimizationRun(Base):
    __tablename__ = "optimization_run"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    objective_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    points: Mapped[list["DispatchPoint"]] = relationship(
        "DispatchPoint",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class DispatchPoint(Base):
    __tablename__ = "dispatch_point"
    run_id: Mapped[int] = mapped_column(ForeignKey("optimization_run.id", ondelete="CASCADE"), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    component_type: Mapped[str] = mapped_column(String(30), primary_key=True)   # battery, ev, pv, grid
    component_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    p_charge_kw: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p_discharge_kw: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    soc_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)

    run: Mapped["OptimizationRun"] = relationship("OptimizationRun", back_populates="points")