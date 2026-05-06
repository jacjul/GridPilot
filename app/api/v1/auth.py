from fastapi import Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update
from typing import Annotated
import uuid
from datetime import datetime, timezone

from app.api.v1.router import router_v1
from app.schemas.user import UserRegistration
from app.db.database import get_async_db
from app.models.user import User
from app.models.token import Token
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token_or_401,
    hash_refresh_token,
)
from app.core.settings import settings
from app.core.redis import (
    create_refresh_entries,
    get_refresh_state,
    get_family_jtis,
    revoke_whole_family_redis,
    revoke_whole_family_db,
)

@router_v1.post("/register", status_code=201)
async def register_new_user(user: UserRegistration, db: Annotated[AsyncSession, Depends(get_async_db)]):

    result = await db.execute(select(User).where(or_(User.email == user.email, User.username == user.username)))
    user_exist = result.scalar_one_or_none()
    if user_exist:
        raise HTTPException(status_code=409, detail="User with that username or email already exists.")
    
    hashed_password = hash_password(user.password)
    dict_user = user.model_dump(exclude={"password"})

    new_user = User(**dict_user, hashed_password=hashed_password)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"message": "created successfully"}

@router_v1.post("/login")
async def login(
    response: Response,
    user: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_async_db)],
):

    result = await db.execute(select(User).where(User.username == user.username))
    user_exist = result.scalar_one_or_none()

    if not user_exist or not verify_password(user.password, user_exist.hashed_password):
        raise HTTPException(status_code=401, detail="User doesnt exist or password is wrong")
    
    access_token = create_access_token(data={"sub": str(user_exist.id)})

    jti_family = uuid.uuid4()
    refresh_token, jti = create_refresh_token(data={"sub": str(user_exist.id), "family": str(jti_family)})

    token_hash = hash_refresh_token(refresh_token)

    #redis
    await create_refresh_entries(jti=jti, jti_family=jti_family, user_id=user_exist.id, token_hash=token_hash)

    #db entry
    new_refresh_token = Token(jti_id=jti, user_id=user_exist.id, jti_family=jti_family, token_hash=token_hash)
    db.add(new_refresh_token)
    await db.commit()
    await db.refresh(new_refresh_token)

    response.set_cookie(
        key="refresh",
        value=refresh_token,
        httponly=True,
        secure=settings.SECURE_COOKIE,
        samesite=settings.SAMESITE_COOKIE.value,
    )

    
    return {"access_token": access_token, "token_type": "bearer"}

@router_v1.post("/refresh")
async def refresh_access_and_refresh_token(
    response: Response,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    
    #get refresh_token
    token = request.cookies.get("refresh")
    if not token:
        raise HTTPException(status_code=401, detail="Didnt send refresh token")
    
    #decode refresh_token
    decoded_refresh_token = decode_token_or_401(token, "refresh")

    jti_raw = decoded_refresh_token.get("jti")
    if not jti_raw:
        raise HTTPException(status_code=401, detail="Missing token jti")

    try:
        old_jti = uuid.UUID(jti_raw)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token jti")

    user_id, status, family, stored_token_hash = await get_refresh_state(str(old_jti))

    if not user_id or not family or not stored_token_hash:
        raise HTTPException(status_code=401, detail="Token state not found")

    if hash_refresh_token(token) != stored_token_hash:
        raise HTTPException(status_code=401, detail="Refresh token mismatch")

    if status != "active":
        jti_list_revoke = await get_family_jtis(str(family))
        await revoke_whole_family_redis(jti_list_revoke)
        await revoke_whole_family_db(uuid.UUID(family), db)
        raise HTTPException(status_code=401, detail="Refresh token reuse detected. Session family revoked")
    
    user_id_int = int(user_id)
    family_uuid = uuid.UUID(family)

    new_access_token = create_access_token(data={"sub": str(user_id_int)})

    new_refresh_token, new_jti = create_refresh_token(data={"sub": str(user_id_int), "family": str(family_uuid)})

    token_hash = hash_refresh_token(new_refresh_token)
    await create_refresh_entries(
        jti=new_jti,
        jti_family=family_uuid,
        user_id=user_id_int,
        token_hash=token_hash,
        old_jti=old_jti,
    )
    
    #db entry
    new_token = Token(jti_id=new_jti, user_id=user_id_int, jti_family=family_uuid, token_hash=token_hash)
    
    #revoked in db 
    await db.execute(
        update(Token)
        .where(Token.jti_id == old_jti)
        .values(revoked=True, revoked_at=datetime.now(timezone.utc))
    )
    
    
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)

    response.set_cookie(
        key="refresh",
        value=new_refresh_token,
        httponly=True,
        secure=settings.SECURE_COOKIE,
        samesite=settings.SAMESITE_COOKIE.value,
    )

    return {"access_token": new_access_token, "token_type": "bearer"}

    


    