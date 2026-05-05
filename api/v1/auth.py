from fastapi import Depends,HTTPException,Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Annotated
import uuid

from app.api.v1.router import router_v1
from app.schemas.user import  UserRegistration
from app.db.database import get_async_db
from app.models.user import User
from app.core.security import hash_password,verify_password,create_access_token,create_refresh_token
from app.core.settings import settings 

oauth2password = OAuth2PasswordBearer(tokenUrl="/api/login")

@router_v1.post("/register")
async def register_new_user(user:UserRegistration,db: Annotated[AsyncSession, Depends(get_async_db)]):

    result= await db.execute(select(User).where(or_ (User.email ==user.email,User.username==user.username )))
    user_exist = result.scalar_one_or_none()
    if user_exist:
        raise HTTPException(status_code=409, detail="User with that username or email already exists.")
    
    hashed_password = hash_password(user.password)
    dict_user =user.model_dump(exclude={"password"})

    new_user = User(**dict_user, hashed_password = hashed_password)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

@router_v1.post("/login")
async def login(response:Response, user:Annotated[OAuth2PasswordRequestForm, Depends()], db:Annotated[AsyncSession,Depends(get_async_db)]):

    result = await db.execute(select(User).where(User.username==user.username))
    user_exist = result.scalar_one_or_none()

    if not user_exist or not verify_password(user.password, user_exist.hashed_password):
        raise HTTPException(status_code=404, detail="User doesnt exist or password is wrong")
    
    access_token = create_access_token(data={"sub": user.username})

    jti_family = str(uuid.uuid4())
    refresh_token,jti = create_refresh_token(data={"sub": user.username, "family":jti_family})

    response.set_cookie(key="refresh", value=refresh_token, 
                        httponly=True ,secure=settings.SECURE_COOKIE ,
                        samesite=settings.SAMESITE_COOKIE)
    
    return {"access_token":access_token , "token_type":"bearer"}


    