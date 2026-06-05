import hmac
import secrets
from fastapi import HTTPException, Request, Response

from app.core.settings import settings

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def issue_csrf_cookie(response: Response) -> str:
    csrf = secrets.token_urlsafe(32)

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf,
        secure=settings.SECURE_COOKIE,
        samesite=settings.SAMESITE_COOKIE.value,
        httponly=False,
    )
    return csrf


def validate_csrf_cookie(request: Request) -> None:
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(CSRF_HEADER_NAME, "").strip()

    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")