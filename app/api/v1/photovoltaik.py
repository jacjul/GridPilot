from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated,Optional 
from datetime import date

from app.api.v1.router import router_v1
from app.db.database import get_async_db
from app.services.photovoltaik_service import PVForecastService
from app.services.auth_service import get_current_user
from app.schemas.user import UserMe
from app.schemas.photovoltaik import PVform,PVOut,PVUpdateForm
from app.models.user import User

pv_service_singleton = PVForecastService()

def get_pv_service():
    return pv_service_singleton



@router_v1.post("/pv")
async def create_PV(formData:PVform,
                    user:Annotated[UserMe,Depends(get_current_user)],
                    db:Annotated[AsyncSession,Depends(get_async_db)],
                    pv_service:Annotated[PVForecastService,Depends(get_pv_service)]):
    
    result = await pv_service.create_new_PV(formData, user,db)

    return result

@router_v1.get("/pv", response_model = list[PVOut])
async def get_PVs(user:Annotated[UserMe,Depends(get_current_user)],
                    db:Annotated[AsyncSession,Depends(get_async_db)],
                    pv_service:Annotated[PVForecastService,Depends(get_pv_service)]):
    
    result = await pv_service.get_PV_data(user,db)
    return result 

@router_v1.get("/pv/{pv_id}", response_model=PVOut)
async def get_single_pv(pv_id:int,
                    user:Annotated[UserMe,Depends(get_current_user)],
                    db:Annotated[AsyncSession,Depends(get_async_db)],
                    pv_service:Annotated[PVForecastService,Depends(get_pv_service)]):

    return await pv_service.get_single_PV(pv_id,user,db)

@router_v1.patch("/pv/{pv_id}")
async def update_PV(pv_id:int,
                    formData:PVUpdateForm,
                    user:Annotated[UserMe,Depends(get_current_user)],
                    db:Annotated[AsyncSession,Depends(get_async_db)],
                    pv_service:Annotated[PVForecastService,Depends(get_pv_service)]):

    return await pv_service.update_PV(pv_id, formData, user, db)

@router_v1.delete("/pv/{pv_id}")
async def delete_PV(pv_id:int,
                    user:Annotated[UserMe,Depends(get_current_user)],
                    db:Annotated[AsyncSession,Depends(get_async_db)],
                    pv_service:Annotated[PVForecastService,Depends(get_pv_service)]):

    return await pv_service.delete_PV(pv_id, user, db)
    

@router_v1.post("/forecastPV/{pv_id}")
@router_v1.post("/forecastPV/")
async def get_forecast_PV(user:Annotated[UserMe,Depends(get_current_user)],
                          db:Annotated[AsyncSession,Depends(get_async_db)],
                          pv_service:Annotated[PVForecastService,Depends(get_pv_service)],
                          pv_id:Optional[int]=None,target_days:Optional[list[date]]=None):
    if pv_id is None:
        return await pv_service.get_forecast_for_pvs(
            db=db,
            pv_owner_id=user.id,
            target_days=target_days,
        )

    return await pv_service.get_forecast_for_pv(
        db=db,
        pv_id=pv_id,
        pv_owner_id=user.id,
        target_days=target_days,
    )
