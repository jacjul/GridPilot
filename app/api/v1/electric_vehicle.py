from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import get_current_user
from app.api.v1.router import router_v1
from app.schemas.user import UserMe
from app.db.database import get_async_db

@router_v1.post("/createEV")
async def create_new_ev(user:Annotated[UserMe,Depends(get_current_user)],
                        db:Annotated[AsyncSession, Depends(get_async_db)])
