from redis.asyncio import  Redis
from datetime import datetime,timezone,timedelta
from typing import Optional,cast,Any

from app.core.settings import settings

r = cast(Any,Redis.from_url(settings.REDIS_URL, decode_responses=True))

async def get_refresh_state(jti: str) -> tuple[str|None,str|None,str|None]:
    key = f"auth:rt:jti:{jti}"
    user_id = await r.hget(key, "user_id")
    status = await r.hget(key, "status")
    family = await r.hget(key, "family")
    return  user_id,  status,  family

async def get_family_jtis(family: str) -> set[str]:
    return await r.smembers(f"auth:rt:jti_family:{family}")
async def create_refresh_entries(jti,jti_family,user_id,token_hash,old_jti=None):



    now_ts =  datetime.now(timezone.utc)
    time_seconds = 60*60*24*settings.REFRESH_TOKEN_DAYS
    exp_ts = (now_ts + timedelta(seconds=time_seconds )).timestamp()

    #keys 
    key_jti = f"auth:rt:jti:{str(jti)}"
    key_jti_family = f"auth:rt:jti_family:{str(jti_family)}"
    key_user_id = f"auth:rt:user_id:{str(user_id)}"

    pipe = r.pipeline()

    if old_jti:
        pipe.hset(old_jti,mapping={"status":"rotated"})

    pipe.hset(name=key_jti, mapping={
        "user_id": str(user_id),
        "jti": str(jti),
        "family": str(jti_family),
        "type": "refresh",
        "status": "active",          # active | rotated | revoked
        "token_hash": token_hash,    # hashed refresh token
        "iat": str(int(now_ts.timestamp())),
        "exp": str(int(exp_ts)),
    })
    pipe.expire(key_jti,time_seconds)

    pipe.sadd(key_jti_family, str(jti))
    pipe.expire(key_jti_family,time_seconds)
    pipe.sadd(key_user_id, str(jti))
    pipe.expire(key_user_id,time_seconds)

    await pipe.execute()

async def revoke_whole_family(jti_set:list):

    pipe =r.pipeline()

    for jti_old in jti_set:
        #continueu he