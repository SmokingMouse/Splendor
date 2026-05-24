from __future__ import annotations

from fastapi import APIRouter

from ..errors import DomainError, as_http_exception
from ..schemas import ProjectCreate, ProjectView
from ...train.project_service import project_service

router = APIRouter()


@router.post("", response_model=ProjectView, status_code=201)
def create_project(payload: ProjectCreate) -> ProjectView:
    try:
        project = project_service.create_project(payload.name, payload.dataset_ids, payload.description)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ProjectView(
        id=project.id,
        name=project.name,
        description=project.description,
        dataset_ids=project.dataset_ids,
        status=project.status,
        latest_run_id=project.latest_run_id,
    )


@router.get("/{project_id}", response_model=ProjectView)
def get_project(project_id: str) -> ProjectView:
    try:
        project = project_service.get_project(project_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ProjectView(
        id=project.id,
        name=project.name,
        description=project.description,
        dataset_ids=project.dataset_ids,
        status=project.status,
        latest_run_id=project.latest_run_id,
    )
