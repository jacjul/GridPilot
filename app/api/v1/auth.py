from fastapi import Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated,TYPE_CHECKING

from app.api.v1.router import router_v1
from app.schemas.user import UserRegistration
from app.db.database import get_async_db
from app.core.settings import settings
from app.services.auth_service import login_issue_tokens, refresh_issue_tokens, register_user

from app.core.limiter import limiter



@router_v1.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register_new_user(request:Request, user: UserRegistration, db: Annotated[AsyncSession, Depends(get_async_db)]):
    await register_user(db, user)

    return {"message": "created successfully"}

@router_v1.post("/login")
@limiter.limit("5/minute")
async def login(
    response: Response,
    request:Request,
    user: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_async_db)],
):

    access_token, refresh_token = await login_issue_tokens(db, user.username, user.password)

    response.set_cookie(
        key="refresh",
        value=refresh_token,
        httponly=True,
        secure=settings.SECURE_COOKIE,
        samesite=settings.SAMESITE_COOKIE.value,
    )

    
    return {"access_token": access_token, "token_type": "bearer"}

@router_v1.post("/refresh")
@limiter.limit("5/minute")
async def refresh_access_and_refresh_token(
    response: Response,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    
    token = request.cookies.get("refresh")
    if not token:
        raise HTTPException(status_code=401, detail="Didnt send refresh token")
    new_access_token, new_refresh_token = await refresh_issue_tokens(db, token)

    response.set_cookie(
        key="refresh",
        value=new_refresh_token,
        httponly=True,
        secure=settings.SECURE_COOKIE,
        samesite=settings.SAMESITE_COOKIE.value,
    )

    return {"access_token": new_access_token, "token_type": "bearer"}

@router_v1.post("/logout")
@limiter.limit("5/minute")
async def logout(response: Response, request:Request, db:Annotated[AsyncSession, Depends(get_async_db)]):

    _ = request.cookies.get("refresh")

    response.delete_cookie(
        key="refresh",
        httponly=True,
        secure=settings.SECURE_COOKIE,
        samesite=settings.SAMESITE_COOKIE.value,
    )

    return {"message": "logged out"}

    


    