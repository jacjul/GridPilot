from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated,Optional 

from app.api.v1.router import router_v1
from app.db.database import get_async_db
from app.services.photovoltaik_service import PVForecastService
from app.services.auth_service import get_current_user
from app.schemas.user import UserMe
from app.schemas.photovoltaik import PVform
from app.models.user import User

def get_pv_service():
    pv_service = PVForecastService()
    return pv_service

@router_v1.post("/createPV")
async def create_PV(formData:PVform,
                    user:Annotated[UserMe,Depends(get_current_user)],
                    db:Annotated[AsyncSession,Depends(get_async_db)],
                    pv_service:Annotated[PVForecastService,Depends(get_pv_service)]):
    
    result = await pv_service.create_new_PV(formData, user,db)

    return result

@router_v1.post("/forecastPV/{pv_id}")
@router_v1.post("/forecastPV/")
async def get_forecast_PV(user:Annotated[UserMe,Depends(get_current_user)],
                          db:Annotated[AsyncSession,Depends(get_async_db)],
                          pv_service:Annotated[PVForecastService,Depends(get_pv_service)],
                          pv_id:Optional[int]):
    
    
    dict_forecast =  await pv_service.get_forecast_for_pv(db=db,pv_id=pv_id, pv_owner_id = user.id)

    return dict_forecast
