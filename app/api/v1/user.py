from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router_v1
from app.db.database import get_async_db
from app.schemas.user import UserMe
from app.services.auth_service import get_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


@router_v1.get("/me", response_model=UserMe)
async def current_user(
	token: Annotated[str, Depends(oauth2_scheme)],
	db: Annotated[AsyncSession, Depends(get_async_db)],
):
	return await get_current_user(db, token)











