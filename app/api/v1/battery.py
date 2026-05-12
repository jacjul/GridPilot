from fastapi import Depends
from typing import Annotated,Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router_v1
from app.db.database import get_async_db
from app.services.auth_service import get_current_user
from app.schemas.user import UserMe
from app.schemas.battery import BESSCreateform, BESSUpdateform
from app.services.battery_service import BESSService

def create_class_instance_BESS():
    bess_service = BESSService()
    return bess_service


@router_v1.post("/bess")
async def create_bess(formdata:BESSCreateform,
                user:Annotated[UserMe, Depends(get_current_user)],
                db: Annotated[AsyncSession, Depends(get_async_db)],
                bess_service:Annotated[BESSService,Depends(create_class_instance_BESS)]):
    result = await bess_service.create_bess(formdata,user,db)
    return result

@router_v1.patch("/bess/{bess_id}")
async def update_bess(bess_id:int, formdata:BESSUpdateform,
                user:Annotated[UserMe, Depends(get_current_user)],
                db: Annotated[AsyncSession, Depends(get_async_db)],
                bess_service:Annotated[BESSService,Depends(create_class_instance_BESS)]):
    result = await bess_service.update_bess(bess_id,formdata,user,db)
    return result

@router_v1.delete("/bess/{bess_id}")
async def delete_bess(bess_id:int,
                user:Annotated[UserMe, Depends(get_current_user)],
                db: Annotated[AsyncSession, Depends(get_async_db)],
                bess_service:Annotated[BESSService,Depends(create_class_instance_BESS)]):
    result = await bess_service.delete_bess(bess_id,user,db)
    return result

@router_v1.get("/bess/{bess_id}")
@router_v1.get("/bess")
async def create_bess(bess_id:Annotated[Optional[int], None],
                user:Annotated[UserMe, Depends(get_current_user)],
                db: Annotated[AsyncSession, Depends(get_async_db)],
                bess_service:Annotated[BESSService,Depends(create_class_instance_BESS)]):
    result = await bess_service.get_bess(bess_id,user,db)
    return result



