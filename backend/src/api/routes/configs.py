from __future__ import annotations

from fastapi import APIRouter

from ..errors import DomainError, as_http_exception
from ..schemas import ConfigCreate, ConfigReuseRequest, ConfigView
from ...train.config_reuse_service import config_reuse_service
from ...train.config_service import config_service

router = APIRouter()


@router.post("/{project_id}/configs", response_model=ConfigView, status_code=201)
def create_config(project_id: str, payload: ConfigCreate) -> ConfigView:
    try:
        config = config_service.create_config(
            project_id=project_id,
            name=payload.name,
            parameters=payload.parameters,
            seed=payload.seed,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ConfigView(
        id=config.id,
        project_id=config.project_id,
        name=config.name,
        parameters=config.parameters,
        seed=config.seed,
        parent_config_id=config.parent_config_id,
    )


@router.post("/{project_id}/configs/{config_id}/reuse", response_model=ConfigView, status_code=201)
def reuse_config(project_id: str, config_id: str, payload: ConfigReuseRequest) -> ConfigView:
    try:
        config = config_reuse_service.reuse(
            project_id=project_id,
            config_id=config_id,
            name=payload.name,
            parameters_override=payload.parameters_override,
            seed=payload.seed,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ConfigView(
        id=config.id,
        project_id=config.project_id,
        name=config.name,
        parameters=config.parameters,
        seed=config.seed,
        parent_config_id=config.parent_config_id,
    )
