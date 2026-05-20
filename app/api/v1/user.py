from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router_v1
from app.db.database import get_async_db
from app.schemas.user import UserConsumptionUpdate, UserMe
from app.services.auth_service import get_current_user, update_user_consumption_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router_v1.get("/me", response_model=UserMe)
async def current_user(
	token: Annotated[str, Depends(oauth2_scheme)],
	db: Annotated[AsyncSession, Depends(get_async_db)],
):
	return await get_current_user(db, token)


@router_v1.patch("/me/consumption", response_model=UserMe)
async def update_my_consumption(
	formdata: UserConsumptionUpdate,
	user: Annotated[UserMe, Depends(get_current_user)],
	db: Annotated[AsyncSession, Depends(get_async_db)],
):
	return await update_user_consumption_service(db=db, user_id=user.id, payload=formdata)











