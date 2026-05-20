from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select,update,delete

from app.schemas.electric_vehicle import EVform,EVUpdateForm,EVDowntimeRuleCreate,EVDowntimeRuleUpdate
from app.schemas.user import UserMe
from app.models.electric_vehicle import ElectricVehicle,EVDowntimeRule

class EV_service():
    @staticmethod
    def _validate_soc_target(value: float | None, label: str) -> None:
        if value is None:
            return
        if value < 0 or value > 100:
            raise HTTPException(status_code=422, detail=f"{label} must be between 0 and 100")

    async def _assert_user_owns_ev(self, ev_id:int, user_id:int,db:AsyncSession):
        owned = await db.scalar(select(ElectricVehicle.id).where(ElectricVehicle.id ==ev_id,
                                            ElectricVehicle.owner_id == user_id ))
        if owned is None:
            raise HTTPException(status_code=403, detail="EV isnt owned by you") 
        
    async def list_user_evs(self, user:UserMe, db:AsyncSession):
        response = await db.execute(select(ElectricVehicle).where(ElectricVehicle.owner_id == user.id))
        evs = response.scalars().all()
        return [
            {
                "id": ev.id,
                "ev_name": ev.ev_name,
                "kw_peak_loading": ev.kw_peak_loading,
                "kwh_battery": ev.kwh_battery,
            }
            for ev in evs
        ]
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

    async def get_single_ev(self, ev_id: int, user: UserMe, db: AsyncSession):
        await self._assert_user_owns_ev(ev_id=ev_id, user_id=user.id, db=db)
        ev = await db.scalar(select(ElectricVehicle).where(ElectricVehicle.id == ev_id))
        if ev is None:
            raise HTTPException(status_code=404, detail="EV not found")
        return {
            "id": ev.id,
            "ev_name": ev.ev_name,
            "kw_peak_loading": ev.kw_peak_loading,
            "kwh_battery": ev.kwh_battery,
        }

    async def update_ev(self, ev_id: int, formdata: EVUpdateForm, user: UserMe, db: AsyncSession):
        await self._assert_user_owns_ev(ev_id=ev_id, user_id=user.id, db=db)
        patch_data = formdata.model_dump(exclude_unset=True, exclude_none=True)
        if not patch_data:
            raise HTTPException(status_code=400, detail="No update data provided")

        if "kw_peak_loading" in patch_data and patch_data["kw_peak_loading"] <= 0:
            raise HTTPException(status_code=422, detail="kw_peak_loading has to be greater then 0")
        if "kwh_battery" in patch_data and patch_data["kwh_battery"] <= 0:
            raise HTTPException(status_code=422, detail="kwh_battery has to be greater then 0")

        try:
            await db.execute(
                update(ElectricVehicle)
                .where(ElectricVehicle.id == ev_id, ElectricVehicle.owner_id == user.id)
                .values(**patch_data)
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Could not update EV")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not update EV")

        return {"message": "success", "ev_id": ev_id}

    async def delete_ev(self, ev_id: int, user: UserMe, db: AsyncSession):
        await self._assert_user_owns_ev(ev_id=ev_id, user_id=user.id, db=db)
        try:
            await db.execute(
                delete(ElectricVehicle).where(ElectricVehicle.id == ev_id, ElectricVehicle.owner_id == user.id)
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Could not delete EV")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Could not delete EV")

        return {"message": "success", "ev_id": ev_id}
    
    async def create_new_blocker(self, formdata:EVDowntimeRuleCreate,user:UserMe,db:AsyncSession):
        
        await self._assert_user_owns_ev(ev_id = formdata.ev_id, user_id = user.id ,db=db)
        self._validate_soc_target(formdata.soc_target_start_pct, "soc_target_start_pct")
        self._validate_soc_target(formdata.soc_target_end_pct, "soc_target_end_pct")
   
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
        self._validate_soc_target(formdata.soc_target_start_pct, "soc_target_start_pct")
        self._validate_soc_target(formdata.soc_target_end_pct, "soc_target_end_pct")

        
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
            soc_target_start_pct = formdata.soc_target_start_pct,
            soc_target_end_pct = formdata.soc_target_end_pct,
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

    async def list_downtime_rules(self, ev_id: int, user: UserMe, db: AsyncSession):
        await self._assert_user_owns_ev(ev_id=ev_id, user_id=user.id, db=db)

        result = await db.execute(
            select(EVDowntimeRule)
            .where(EVDowntimeRule.ev_id == ev_id)
            .order_by(EVDowntimeRule.id.asc())
        )
        rules = result.scalars().all()

        return [
            {
                "id": rule.id,
                "ev_id": rule.ev_id,
                "weekdays_mask": rule.weekdays_mask,
                "start_time": rule.start_time,
                "end_time": rule.end_time,
                "valid_from": rule.valid_from,
                "valid_to": rule.valid_to,
                "soc_target_start_pct": rule.soc_target_start_pct,
                "soc_target_end_pct": rule.soc_target_end_pct,
                "tz_name": rule.tz_name,
            }
            for rule in rules
        ]

        





            

