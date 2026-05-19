from fastapi import Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserMe
from app.db.database import get_async_db
from app.services.auth_service import get_current_user
from app.api.v1.router import router_v1
from app.schemas.electricity import ElectricityCreateform,ElectricityUpdateForm,ElectricityOut
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

@router_v1.get("/electricity", response_model=list[ElectricityOut])
@router_v1.get("/electricity/{tariff_id}", response_model=ElectricityOut)
async def get_electricity_tarifs(user:Annotated[UserMe,Depends(get_current_user)],
                                db:Annotated[AsyncSession, Depends(get_async_db)],
                                service:Annotated[ElectricityService, Depends(create_service)],
                                tariff_id:int|None=None):

    return await service.get_tariffs(user, db, tariff_id=tariff_id)

@router_v1.patch("/electricity/{tariff_id}")
async def update_electricity_tarif(tariff_id:int,
                                formdata:ElectricityUpdateForm,
                                user:Annotated[UserMe,Depends(get_current_user)],
                                db:Annotated[AsyncSession, Depends(get_async_db)],
                                service:Annotated[ElectricityService, Depends(create_service)]):
    return await service.update_tariff(tariff_id, formdata, user, db)

@router_v1.delete("/electricity/{tariff_id}")
async def delete_electricity_tarif(tariff_id:int,
                                user:Annotated[UserMe,Depends(get_current_user)],
                                db:Annotated[AsyncSession, Depends(get_async_db)],
                                service:Annotated[ElectricityService, Depends(create_service)]):
    return await service.delete_tariff(tariff_id, user, db)