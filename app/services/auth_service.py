from datetime import datetime, timezone
import uuid
from fastapi import HTTPException,Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from redis.exceptions import RedisError

from app.core.redis import (
    create_refresh_entries,
    get_family_jtis,
    get_refresh_state,
    revoke_whole_family_db,
    revoke_whole_family_redis,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_or_401,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.token import Token
from app.models.user import User
from app.schemas.user import LoadProfileType, UserConsumptionUpdate, UserMe, UserRegistration
from app.db.database import get_async_db

oauth2passwordbearer = OAuth2PasswordBearer(tokenUrl="/api/login")


def _normalize_load_profile_type(value: str) -> LoadProfileType:
    return "SLP_HEATPUMP" if value == "SLP_HEATPUMP" else "SLP"


async def register_user(db: AsyncSession, user: UserRegistration) -> None:
    result = await db.execute(
        select(User).where(or_(User.email == user.email, User.username == user.username))
    )
    user_exist = result.scalar_one_or_none()
    if user_exist:
        raise HTTPException(status_code=409, detail="User with that username or email already exists.")

    hashed_password = hash_password(user.password)
    dict_user = user.model_dump(exclude={"password"})

    new_user = User(**dict_user, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)


async def login_issue_tokens(db: AsyncSession, username: str, password: str) -> tuple[str, str]:
    result = await db.execute(select(User).where(User.username == username))
    user_exist = result.scalar_one_or_none()

    if not user_exist or not verify_password(password, user_exist.hashed_password):
        raise HTTPException(status_code=401, detail="User doesnt exist or password is wrong")

    access_token = create_access_token(data={"sub": str(user_exist.id)})

    jti_family = uuid.uuid4()
    refresh_token, jti = create_refresh_token(
        data={"sub": str(user_exist.id), "family": str(jti_family)}
    )

    token_hash = hash_refresh_token(refresh_token)

    try:
        await create_refresh_entries(
            jti=jti,
            jti_family=jti_family,
            user_id=user_exist.id,
            token_hash=token_hash,
        )
    except RedisError:
        raise HTTPException(status_code=503, detail="Auth session store unavailable")

    new_refresh_token = Token(
        jti_id=jti,
        user_id=user_exist.id,
        jti_family=jti_family,
        token_hash=token_hash,
    )
    db.add(new_refresh_token)
    await db.commit()

    return access_token, refresh_token


async def refresh_issue_tokens(db: AsyncSession, refresh_token_raw: str) -> tuple[str, str]:
    decoded_refresh_token = decode_token_or_401(refresh_token_raw, "refresh")

    jti_raw = decoded_refresh_token.get("jti")
    if not jti_raw:
        raise HTTPException(status_code=401, detail="Missing token jti")

    try:
        old_jti = uuid.UUID(jti_raw)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token jti")

    try:
        user_id, status, family, stored_token_hash = await get_refresh_state(str(old_jti))
    except RedisError:
        raise HTTPException(status_code=503, detail="Auth session store unavailable")

    if not user_id or not family or not stored_token_hash:
        raise HTTPException(status_code=401, detail="Token state not found")

    if hash_refresh_token(refresh_token_raw) != stored_token_hash:
        raise HTTPException(status_code=401, detail="Refresh token mismatch")

    if status != "active":
        try:
            jti_list_revoke = await get_family_jtis(str(family))
            await revoke_whole_family_redis(jti_list_revoke)
        except RedisError:
            raise HTTPException(status_code=503, detail="Auth session store unavailable")
        await revoke_whole_family_db(uuid.UUID(family), db)
        raise HTTPException(status_code=401, detail="Refresh token reuse detected. Session family revoked")

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token user identifier")

    try:
        family_uuid = uuid.UUID(family)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token family identifier")

    new_access_token = create_access_token(data={"sub": str(user_id_int)})
    new_refresh_token, new_jti = create_refresh_token(
        data={"sub": str(user_id_int), "family": str(family_uuid)}
    )

    token_hash = hash_refresh_token(new_refresh_token)
    try:
        await create_refresh_entries(
            jti=new_jti,
            jti_family=family_uuid,
            user_id=user_id_int,
            token_hash=token_hash,
            old_jti=old_jti,
        )
    except RedisError:
        raise HTTPException(status_code=503, detail="Auth session store unavailable")

    new_token = Token(
        jti_id=new_jti,
        user_id=user_id_int,
        jti_family=family_uuid,
        token_hash=token_hash,
    )

    await db.execute(
        update(Token)
        .where(Token.jti_id == old_jti)
        .values(revoked=True, revoked_at=datetime.utcnow())
    )

    db.add(new_token)
    await db.commit()

    return new_access_token, new_refresh_token

async def get_current_user(db: Annotated[AsyncSession, Depends(get_async_db)],
                            access_token:Annotated[str,Depends(oauth2passwordbearer)])->UserMe:
    return await get_current_user_service(db,access_token )

async def get_current_user_service(db: AsyncSession, access_token: str) -> UserMe:
    decoded_access_token = decode_token_or_401(access_token, "access")

    user_id_raw = decoded_access_token.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=401, detail="Missing user identifier in access token")

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid user identifier in access token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserMe(
        id=user.id,
        name=user.name,
        lastname=user.lastname,
        username=user.username,
        email=user.email,
        annual_consumption_kwh=float(user.annual_consumption_kwh),
        load_profile_type=_normalize_load_profile_type(user.load_profile_type),
    )


async def update_user_consumption_service(
    db: AsyncSession,
    user_id: int,
    payload: UserConsumptionUpdate,
) -> UserMe:
    if payload.annual_consumption_kwh <= 0:
        raise HTTPException(status_code=422, detail="annual_consumption_kwh must be > 0")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.annual_consumption_kwh = payload.annual_consumption_kwh
    user.load_profile_type = payload.load_profile_type
    await db.commit()
    await db.refresh(user)

    return UserMe(
        id=user.id,
        name=user.name,
        lastname=user.lastname,
        username=user.username,
        email=user.email,
        annual_consumption_kwh=float(user.annual_consumption_kwh),
        load_profile_type=_normalize_load_profile_type(user.load_profile_type),
    )

