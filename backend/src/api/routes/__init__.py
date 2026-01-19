from fastapi import APIRouter

from .actions import router as actions_router
from .ai_configs import router as ai_configs_router
from .matches import router as matches_router

api_router = APIRouter()
api_router.include_router(matches_router, prefix="/matches")
api_router.include_router(actions_router, prefix="/matches/{match_id}/actions")
api_router.include_router(ai_configs_router, prefix="/ai-configs")
