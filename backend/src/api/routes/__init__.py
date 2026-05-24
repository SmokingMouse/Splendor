from fastapi import APIRouter

from .actions import router as actions_router
from .ai_configs import router as ai_configs_router
from .artifacts import router as artifacts_router
from .configs import router as configs_router
from .datasets import router as datasets_router
from .evaluations import router as evaluations_router
from .matches import router as matches_router
from .projects import router as projects_router
from .runs import router as runs_router

api_router = APIRouter()
api_router.include_router(matches_router, prefix="/matches")
api_router.include_router(actions_router, prefix="/matches/{match_id}/actions")
api_router.include_router(ai_configs_router, prefix="/ai-configs")
api_router.include_router(projects_router, prefix="/projects")
api_router.include_router(datasets_router, prefix="/datasets")
api_router.include_router(configs_router, prefix="/projects")
api_router.include_router(runs_router)
api_router.include_router(artifacts_router, prefix="/artifacts")
api_router.include_router(evaluations_router, prefix="/evaluations")
