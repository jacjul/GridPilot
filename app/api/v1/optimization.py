from fastapi import Depends, Query
from typing import Annotated 
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router_v1
from app.schemas.user import UserMe
from app.services.auth_service import get_current_user
from app.db.database import get_async_db
from app.services.optimization_service import OptimizationService
def create_service_optimization():
    service_instance = OptimizationService()
    return service_instance

@router_v1.post("/optimization/day_ahead")
async def optimize_day_ahead(user:Annotated[UserMe, Depends(get_current_user)],
                             db: Annotated[AsyncSession, Depends(get_async_db)],
                             service:Annotated[OptimizationService,Depends(create_service_optimization)],
                             horizon_days: Annotated[int, Query(ge=1, le=2)] = 1,
                             enforce_terminal_bess_soc: bool | None = None):
    
    result = await service.run_day_ahead(
        user,
        db,
        horizon_days=horizon_days,
        enforce_terminal_bess_soc=enforce_terminal_bess_soc,
    )
    return result