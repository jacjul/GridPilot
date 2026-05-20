from fastapi import Depends
from fastapi.responses import JSONResponse
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.database import get_async_db
from app.api.v1.router import router_v1
from app.core.redis import r 
@router_v1.get("/healthz")
async def health_check():
    return {"status":"ok"}

@router_v1.get("/readyz")
async def ready(db:Annotated[AsyncSession,Depends(get_async_db)]):
    checks = {}
    errors = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] ="ok"
    except Exception as exc:
        checks["database"] = "down"
        errors["database"] = str(exc)

    try:
        await r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = "down"
        errors["redis"] = str(exc)
    
    if errors:
        return JSONResponse(
            status_code = 503,
            content={
                "status" :"not_ready",
                "checks" : checks,
                "errors" : errors
            }
        )
    return {"status":"ready", "checks":checks}