from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.endpoints import contracts, jobs, reports, simulations
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.webhooks import router as webhooks_router

_auth = [Depends(get_current_user)]

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"], dependencies=_auth)
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"], dependencies=_auth)
api_router.include_router(reports.router, prefix="/reports", tags=["reports"], dependencies=_auth)
api_router.include_router(simulations.router, prefix="/simulations", tags=["simulations"], dependencies=_auth)
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
