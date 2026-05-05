from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy import Float,ForeignKey
from typing import TYPE_CHECKING

from app.db.database import Base
if TYPE_CHECKING:
    from app.models.user import User

class Battery(Base):
    __tablename__ = "battery"

    id: Mapped[int] = mapped_column(primary_key =True)
    name:Mapped[str] = mapped_column(nullable=True)
    kw_peak_charge:Mapped[float] = mapped_column(Float, nullable=False)
    kw_peak_discharge:Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=lambda context: context.get_current_parameters()["kw_peak_charge"],
    )
    kwh:Mapped[float] = mapped_column(Float, nullable=False)
    owner_id:Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner:Mapped["User"] = relationship("User", back_populates="battery_owned")


