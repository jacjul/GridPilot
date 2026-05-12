from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from sqlalchemy import select,update,delete
from typing import Optional

from app.schemas.battery import BESSCreateform,BESSUpdateform
from app.schemas.user import UserMe
from app.models.battery import Battery
class BESSService():

    async def _assert_that_bess_owned_by_user(self, bess_id:int, user_id:int, db:AsyncSession):

        result = await db.execute(select(Battery).where(Battery.id ==bess_id, Battery.owner_id ==user_id))
        bess = result.scalar_one_or_none()
        if not bess:
            raise HTTPException(status_code=403, detail = "Bess not found or not owned by you")
        return bess
    def _validation_values(self,dict_validation:dict):
        for value in dict_validation.values():
            if isinstance(value,float):
                if value <=0:
                    raise HTTPException(status_code=422, detail="kw_peak and kwh should be higher then 0")
    async def create_bess(self, formdata:BESSCreateform,user:UserMe,db:AsyncSession):
  
        kw_peak_discharge = (
            formdata.kw_peak_discharge
            if formdata.kw_peak_discharge is not None
            else formdata.kw_peak_charge
)
        try:
            dict_load = formdata.model_dump()
            dict_load.pop("kw_peak_discharge", None)
            dict_load.update({"kw_peak_discharge" :kw_peak_discharge,"owner_id":user.id})

            self._validation_values(dict_load)
            new_battery= Battery(**dict_load)

            db.add(new_battery)
            await db.commit()
            await db.refresh(new_battery)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409 , detail ="Could not integrate in DB")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500 , detail ="DB Error on BESS creation")

        return {"message": "success", "bess_id": new_battery.id}
    
    async def update_bess(self,bess_id, formdata:BESSUpdateform,user:UserMe,db:AsyncSession):

        bess = await self._assert_that_bess_owned_by_user(bess_id=bess_id, user_id=user.id, db=db)

        try:
            patch_data = formdata.model_dump(exclude_unset=True, exclude_none=True)

            self._validation_values(patch_data)

            if not patch_data:
                raise HTTPException(status_code=400, detail="No update data provided")
            await db.execute(update(Battery).where(Battery.id == bess_id)
                            .values(
                                    **patch_data
                            ))
            
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409 , detail ="Could not integrate in DB")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500 , detail ="DB Error on BESS update")
        return {"message": "success", "bess_id": bess_id}
    
    async def delete_bess(self,bess_id,user:UserMe,db:AsyncSession):

        await self._assert_that_bess_owned_by_user(bess_id=bess_id, user_id=user.id, db=db)

        try:
            await db.execute(delete(Battery).where(Battery.id ==bess_id))
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409 , detail ="Could not integrate in DB")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500 , detail ="DB Error on BESS delete")
        return {"message": "success", "bess_id": bess_id}
    async def get_bess(self,bess_id:Optional[int],user:UserMe,db:AsyncSession):

        if bess_id is not None:
            bess = await self._assert_that_bess_owned_by_user(bess_id=bess_id, user_id=user.id, db=db)

            return  {
            "id": bess.id,
            "name": bess.name,
            "kw_peak_charge": bess.kw_peak_charge,
            "kw_peak_discharge": bess.kw_peak_discharge,
            "kwh": bess.kwh,
        }
        
        else:
            result = await db.execute(select(Battery).where(Battery.owner_id == user.id))
            batteries =  result.scalars().all()
            return [
        {
            "id": b.id,
            "name": b.name,
            "kw_peak_charge": b.kw_peak_charge,
            "kw_peak_discharge": b.kw_peak_discharge,
            "kwh": b.kwh,
        }
        for b in batteries
    ]

            



 


