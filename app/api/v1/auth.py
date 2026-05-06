from fastapi import Depends,HTTPException,Response,Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update
from typing import Annotated
import uuid
import jwt
from datetime import datetime,timezone,timedelta

from app.api.v1.router import router_v1
from app.schemas.user import  UserRegistration
from app.db.database import get_async_db
from app.models.user import User
from app.models.token import Token
from app.core.security import hash_password,verify_password,create_access_token,create_refresh_token,decode_token,hash_refresh_token
from app.core.settings import settings 
from app.core.redis import r,create_refresh_entries,get_refresh_state,get_family_jtis,revoke_whole_family

oauth2password = OAuth2PasswordBearer(tokenUrl="/api/login")

@router_v1.post("/register", status_code=201)
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

    return {"message":"created successfully"}

@router_v1.post("/login")
async def login(response:Response, user:Annotated[OAuth2PasswordRequestForm, Depends()], db:Annotated[AsyncSession,Depends(get_async_db)]):

    result = await db.execute(select(User).where(User.username==user.username))
    user_exist = result.scalar_one_or_none()

    if not user_exist or not verify_password(user.password, user_exist.hashed_password):
        raise HTTPException(status_code=401, detail="User doesnt exist or password is wrong")
    
    access_token = create_access_token(data={"sub": user_exist.id})

    jti_family = uuid.uuid4()
    refresh_token,jti = create_refresh_token(data={"sub": user_exist.id, "family":str(jti_family)})

    response.set_cookie(key="refresh", value=refresh_token, 
                        httponly=True ,secure=settings.SECURE_COOKIE ,
                        samesite=settings.SAMESITE_COOKIE.value)

    token_hash = hash_refresh_token(refresh_token)

    #redis
    await create_refresh_entries(jti=jti,jti_family=jti_family,user_id=user_exist.id,token_hash=token_hash)

    #db entry
    new_refresh_token = Token(jti_id= jti, user_id=user_exist.id,
                               jti_family=jti_family,token_hash=token_hash)
    db.add(new_refresh_token)
    await db.commit()
    await db.refresh(new_refresh_token)

    
    return {"access_token":access_token , "token_type":"bearer"}

@router_v1.post("/refresh")
async def refresh_access_and_refresh_token(response:Response,request:Request,db:Annotated[AsyncSession,Depends(get_async_db)]):
    
    token = request.cookies.get("refresh")
    if not token:
        raise HTTPException(status_code=401, detail="Didnt send refresh token")
    
    try:
        decoded_refresh_token = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if not decoded_refresh_token.get("typ") == "refresh":
        raise HTTPException(status_code=401, detail="Wrong token sent")
    
    jti = uuid.UUID(decoded_refresh_token.get("jti"))

    user_id, status, family = await get_refresh_state(str(jti))

    old_jti = f"auth:rt:jti:{str(jti)}" 
    if not user_id:
        raise HTTPException(status_code=401, detail="No token sent") 
    if status != "active":
        # so this would be revoked token and should cause family revocation(?)
        jti_list_revoke = await get_family_jtis(family)
        await revoke_whole_family(jti_list_revoke)
        raise HTTPException(status_code=409, detail="Coud not find redis entry or token inactive")
    
    new_access_token = create_access_token(data={"sub":user_id})

    new_refresh_token,jti = create_refresh_token(data={"sub": user_id, "family":family})

    response.set_cookie(key="refresh", value=new_refresh_token, httponly=True,
                         secure=settings.SECURE_COOKIE,samesite=settings.SAMESITE_COOKIE.value)

    token_hash = hash_refresh_token(new_refresh_token)
    #redis new token
    await create_refresh_entries(jti=jti,jti_family=family,user_id=user_id,token_hash=token_hash,old_jti=old_jti)

    # revoke old token in redis 
    
    #db entry
    new_token = Token(jti_id= jti, user_id=user_id,
                               jti_family=family,token_hash=token_hash)
    
    #revoked in db 
    await db.execute(update(Token).where(Token.jti_id ==old_jti).values(revoked=True, revoked_at=datetime.now(timezone.utc)))
    
    
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)

    return {"access_token": new_access_token, "token_type": "bearer"}

    


    