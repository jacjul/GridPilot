
"""
Production-ready Redis sliding-window rate limiter for FastAPI.
- Atomic Lua script (ZADD/ZREMRANGEBYSCORE)
- X-Forwarded-For support
- Fail-open policy with logging
- Returns headers for rate limit info
"""

import time
import math
import logging
from uuid import uuid4
from typing import Optional
from fastapi import Request, HTTPException, Depends
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from app.core.redis import r

log = logging.getLogger(__name__)

# Sliding-window Lua: ZADD member now, remove old, get count, set expire, return {allowed(1/0), remaining, earliest}
SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZADD', key, now, member)
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
redis.call('PEXPIRE', key, window)
if count > limit then
  local earliest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')[2]
  return {0, count, earliest or 0}
end
return {1, limit - count, 0}
"""

_script_sha: Optional[str] = None

async def _load_script():
    """Load the Lua script into Redis and cache its SHA."""
    global _script_sha
    if _script_sha:
        return _script_sha
    try:
        _script_sha = await r.script_load(SLIDING_WINDOW_LUA)
    except Exception:
        _script_sha = None
    return _script_sha

def _client_ip(request: Request) -> str:
    """Get client IP, respecting X-Forwarded-For if present."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host or "unknown"

def rate_limit_dependency(limit: int, window_seconds: int):
    """
    FastAPI dependency for sliding-window Redis rate limiting.
    Args:
        limit: Max requests per window.
        window_seconds: Window size in seconds.
    Raises:
        HTTPException 429 if rate limit exceeded.
    Returns:
        dict with limit, remaining, reset seconds.
    """
    async def _dep(request: Request):
        key = f"rl:{request.url.path}:{_client_ip(request)}"
        now_ms = int(time.time() * 1000)
        window_ms = int(window_seconds * 1000)
        member = str(uuid4())

        try:
            sha = await _load_script()
            if sha:
                res = await r.evalsha(sha, 1, key, now_ms, window_ms, limit, member)
            else:
                res = await r.eval(SLIDING_WINDOW_LUA, 1, key, now_ms, window_ms, limit, member)
            ok = int(res[0])
            remaining = int(res[1])
            earliest = int(res[2])
        except Exception as exc:
            log.exception("Rate limiter redis error, allowing request (fail-open)")
            return {"limit": limit, "remaining": limit, "reset": 0}

        if ok == 1:
            reset_seconds = 0
            return {"limit": limit, "remaining": remaining, "reset": reset_seconds}
        # rate limited -> compute retry-after
        retry_after = 0
        if earliest and earliest > 0:
            retry_after = math.ceil(max(0, (earliest + window_ms - now_ms) / 1000.0))
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    return Depends(_dep)
