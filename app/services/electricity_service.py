from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import update
from typing import Any
from datetime import datetime, timezone 

from app.schemas.electricity import ElectricityCreateform, MarketZone
from app.schemas.user import UserMe
from app.models.price_electricity import ElectricityPrice
class ElectricityService():
    def _assert_user_data_is_correct(self, formdata:ElectricityCreateform):
        if formdata.price_typ =="fixed" and formdata.fixed_price is None:
            raise HTTPException(status_code =422, detail="When price_typ is fixed a price is needed")
        if formdata.price_typ =="dynamic_EPEX" and formdata.fixed_price is not None:
            raise HTTPException(status_code=422, detail="When price_typ is dynamic EPEX the fixed price wont be used")

        if formdata.fixed_price is not None and formdata.fixed_price <0:
            raise HTTPException(status_code =422, detail ="Price has to be higher 0")
            
    def _prepare_for_db_add(self,formdata,user_id:int)->dict[str,Any]:
        if  formdata.name is None:
            if formdata.price_typ =="fixed":
                name = f"fixed {str(formdata.fixed_price)}"
            else:
                if formdata.market_zone:
                    name = f"dynamic_EPEX {formdata.market_zone}"
                else:
                    name = "dynamic_EPEX DE-LU"
        else:
            name = formdata.name 

        if formdata.price_typ =="dynamic_EPEX":
            market_zone = formdata.market_zone if formdata.market_zone is not None else MarketZone.DE_LU
    
        data = formdata.model_dump(exclude={"name", "market_zone"},exclude_unset =True, exclude_none=True)
        if formdata.price_typ =="dynamic_EPEX":
            data.update({"name":name, "market_zone":market_zone, "owner_id":user_id})
        else:
            data.update({"name":name, "owner_id":user_id,})
        return data
    async def _set_old_price_inactive(self, user_id,db):
        await db.execute(update(ElectricityPrice).where(ElectricityPrice.owner_id == user_id).values(is_active=False))
        await db.flush()
    async def create_electricity_tarif(self,formdata:ElectricityCreateform,user:UserMe,db:AsyncSession):
        self._assert_user_data_is_correct(formdata)

        data_to_upload = self._prepare_for_db_add(formdata,user.id)

        await self._set_old_price_inactive(user.id,db=db)

        try:
            new_price = ElectricityPrice(**data_to_upload,is_active=True, updated_at = datetime.now(timezone.utc))
            db.add(new_price)
            await db.commit()
            await db.refresh(new_price)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail = "Tariff conflict")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code = 500, detail ="Error when writing to DB") 
        return {"message": "success", "new_price_id": new_price.id} 
