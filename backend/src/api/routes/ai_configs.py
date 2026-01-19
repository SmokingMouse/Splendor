from __future__ import annotations

from fastapi import APIRouter

from ..schemas import AiConfig, AiConfigList
from ...engine.ai_config import load_ai_configs
from ...infra.config import load_settings

router = APIRouter()


@router.get("", response_model=AiConfigList)
def list_ai_configs() -> AiConfigList:
    settings = load_settings()
    configs = load_ai_configs(settings.ai_config_path)
    return AiConfigList(
        configs=[
            AiConfig(id=cfg.id, name=cfg.name, description=cfg.description)
            for cfg in configs
        ]
    )
