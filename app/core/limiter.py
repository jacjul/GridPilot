from slowapi import Limiter,_rate_limit_exceeded_handler
from fastapi import Request
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

def rate_limit_key(request:Request):
    user = getattr(request.state,"user",None)

    if user:
        return f"user_id:{user.id}"
    else:
        try:
            ip = get_remote_address(request)
        except Exception:
            ip = "unknown"
        return f"ip:{ip}"
    

limiter = Limiter(key_func=rate_limit_key, default_limits=["200/min"], swallow_errors=True)