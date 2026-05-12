from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import get_current_user
from app.api.v1.router import router_v1
from app.schemas.user import UserMe
from app.db.database import get_async_db
from app.schemas.electric_vehicle import EVform,EVDowntimeRuleCreate,EVDowntimeRuleUpdate
from app.services.electric_vehicle_service import EV_service

def create_EV_instance():
    ev_service = EV_service()
    return ev_service



@router_v1.get("/ev")
async def get_all_evs(user:Annotated[UserMe,Depends(get_current_user)],
                db:Annotated[AsyncSession, Depends(get_async_db)],
                ev_service:Annotated[EV_service, Depends(create_EV_instance)]):
    
    response = await ev_service.list_user_evs(user,db)
    return response

@router_v1.post("/ev")
async def create_new_ev(formdata:EVform,
                        user:Annotated[UserMe,Depends(get_current_user)],
                        db:Annotated[AsyncSession, Depends(get_async_db)],
                        ev_service:Annotated[EV_service, Depends(create_EV_instance)]):
    
    response = await ev_service.create_new_EV(formdata, user,db)
    return response

@router_v1.post("/ev/{ev_id}/downtime-rules")
async def create_blocker_EV(ev_id:int,
                            formdata:EVDowntimeRuleCreate, 
                            user:Annotated[UserMe,Depends(get_current_user)],
                        db:Annotated[AsyncSession, Depends(get_async_db)],
                        ev_service:Annotated[EV_service, Depends(create_EV_instance)]):
    if formdata.ev_id != ev_id:
        raise HTTPException(status_code=400, detail="ev_id path param and payload must match")

    response = await ev_service.create_new_blocker(formdata,user,db)
    return response    

@router_v1.patch("/ev/{ev_id}/downtime-rules/{rule_id}")
async def update_blocker(ev_id:int,
                        rule_id:int,
                        formdata:EVDowntimeRuleUpdate, 
                            user:Annotated[UserMe,Depends(get_current_user)],
                        db:Annotated[AsyncSession, Depends(get_async_db)],
                        ev_service:Annotated[EV_service, Depends(create_EV_instance)]):
    response = await ev_service.update_new_blocker(ev_id, rule_id, formdata, user, db)
    return response   

@router_v1.delete("/ev/{ev_id}/downtime-rules/{rule_id}")
async def delete_blocker(ev_id:int,
                        rule_id:int,
                            user:Annotated[UserMe,Depends(get_current_user)],
                        db:Annotated[AsyncSession, Depends(get_async_db)],
                        ev_service:Annotated[EV_service, Depends(create_EV_instance)]):
    response = await ev_service.delete_new_blocker(ev_id, rule_id, user, db)
    return response   


    




