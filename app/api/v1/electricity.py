from fastapi import Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserMe
from app.db.database import get_async_db
from app.services.auth_service import get_current_user
from app.api.v1.router import router_v1
from app.schemas.electricity import ElectricityCreateform
from app.services.electricity_service import ElectricityService

def create_service():
    electricity_service = ElectricityService()
    return electricity_service

@router_v1.post("/electricity")
async def create_electricity_tarif(formdata:ElectricityCreateform,
                                user:Annotated[UserMe,Depends(get_current_user)],
                                db:Annotated[AsyncSession, Depends(get_async_db)],
                                service:Annotated[ElectricityService, Depends(create_service)]):
    response = await service.create_electricity_tarif(formdata,user,db)
    return response 