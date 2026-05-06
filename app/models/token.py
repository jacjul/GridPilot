from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey,Uuid,func
from typing import TYPE_CHECKING
import uuid
from datetime import datetime

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.user import User
class Token(Base):
    __tablename__ = "token"

    jti_id:Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id:Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    token_hash:Mapped[str]
    jti_family:Mapped[uuid.UUID] = mapped_column(Uuid)
    created_at:Mapped[datetime] =mapped_column(server_default=func.now())
    revoked_at:Mapped[datetime] = mapped_column(nullable=True)
    revoked:Mapped[bool] = mapped_column(default= False)

    user:Mapped["User"] = relationship("User", back_populates="refresh_tokens")


