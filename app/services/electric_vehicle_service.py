from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select,update,delete

from app.schemas.electric_vehicle import EVform,EVDowntimeRuleCreate,EVDowntimeRuleUpdate
from app.schemas.user import UserMe
from app.models.electric_vehicle import ElectricVehicle,EVDowntimeRule

class EV_service():
    async def _assert_user_owns_ev(self, ev_id:int, user_id:int,db:AsyncSession):
        owned = await db.scalar(select(ElectricVehicle.id).where(ElectricVehicle.id ==ev_id,
                                            ElectricVehicle.owner_id == user_id ))
        if owned is None:
            raise HTTPException(status_code=403, detail="EV isnt owned by you") 
        
    async def list_user_evs(self, user:UserMe, db:AsyncSession):
        response = await db.execute(select(ElectricVehicle).where(ElectricVehicle.owner_id == user.id))
        ####evs = response.map
    async def create_new_EV(self,formdata:EVform,user:UserMe,db:AsyncSession):
        if formdata.kw_peak_loading<= 0 or formdata.kwh_battery<= 0:
            raise HTTPException(status_code=422, detail="kw peak and kwh have to be greater then 0")

        try:
            di:dict = formdata.model_dump()
            di.update({"owner_id":user.id})
            new_ev = ElectricVehicle(**di)

            db.add(new_ev)
            await db.commit()
            await db.refresh(new_ev)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="EV conflicts with existing data")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail = "Could not create EV")
        
        return {"message": "success", "ev_id": new_ev.id}
    
    async def create_new_blocker(self, formdata:EVDowntimeRuleCreate,user:UserMe,db:AsyncSession):
        
        await self._assert_user_owns_ev(ev_id = formdata.ev_id, user_id = user.id ,db=db)
   
        new_blocker = EVDowntimeRule(**formdata.model_dump())

        try:
            db.add(new_blocker)
            await db.commit()
            await db.refresh(new_blocker)
            return {"message":"success"}
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Conflicts with existing data")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not create Downtime")
        
    async def update_new_blocker(self, ev_id:int, rule_id:int, formdata:EVDowntimeRuleUpdate,user:UserMe,db:AsyncSession):

        await self._assert_user_owns_ev(ev_id = ev_id, user_id = user.id ,db=db)

        
        try:
            rule_exists = await db.scalar(
                select(EVDowntimeRule.id).where(
                    EVDowntimeRule.id == rule_id,
                    EVDowntimeRule.ev_id == ev_id,
                )
            )
            if rule_exists is None:
                raise HTTPException(status_code=404, detail="Downtime rule not found")

            await db.execute(update(EVDowntimeRule)
                .where(EVDowntimeRule.id == rule_id,
                        EVDowntimeRule.ev_id == ev_id).values(
            weekdays_mask = formdata.weekdays_mask,
            start_time=formdata.start_time, 
            end_time=formdata.end_time, 
            valid_from= formdata.valid_from,
            valid_to = formdata.valid_to,
            tz_name = formdata.tz_name
        ))
            await db.commit()
            return {"message":"success"}
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail ="Could not update downtime rule")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not update Downtime")
        
    async def delete_new_blocker(self, ev_id:int, rule_id:int,user:UserMe,db:AsyncSession):
        
        await self._assert_user_owns_ev(ev_id = ev_id, user_id = user.id ,db=db)

        
        try:
            rule_exists = await db.scalar(
                select(EVDowntimeRule.id).where(
                    EVDowntimeRule.id == rule_id,
                    EVDowntimeRule.ev_id == ev_id,
                )
            )
            if rule_exists is None:
                raise HTTPException(status_code=404, detail="Downtime rule not found")

            await db.execute(delete(EVDowntimeRule).where(
                EVDowntimeRule.id ==rule_id,
                EVDowntimeRule.ev_id == ev_id))

            await db.commit()
            return {"message":"success"}
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail ="Could not delete downtime rule")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not delete Downtime")

        





            

