from __future__ import annotations

from fastapi import APIRouter

from ..errors import DomainError, as_http_exception
from ..schemas import RunCreate, RunView
from ...train.run_service import run_service

router = APIRouter()


@router.post("/projects/{project_id}/runs", response_model=RunView, status_code=201)
def create_run(project_id: str, payload: RunCreate) -> RunView:
    try:
        run = run_service.start_run(project_id, payload.config_id, payload.dataset_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return RunView(
        id=run.id,
        status=run.status,
        metrics_summary=run.metrics_summary,
        error_reason=run.error_reason,
        artifacts=run.artifacts,
        project_id=run.project_id,
        config_id=run.config_id,
        dataset_id=run.dataset_id,
        retry_of=run.retry_of,
    )


@router.get("/runs/{run_id}", response_model=RunView)
def get_run(run_id: str) -> RunView:
    try:
        run = run_service.get_run(run_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return RunView(
        id=run.id,
        status=run.status,
        metrics_summary=run.metrics_summary,
        error_reason=run.error_reason,
        artifacts=run.artifacts,
        project_id=run.project_id,
        config_id=run.config_id,
        dataset_id=run.dataset_id,
        retry_of=run.retry_of,
    )


@router.post("/runs/{run_id}/retry", response_model=RunView, status_code=202)
def retry_run(run_id: str) -> RunView:
    try:
        run = run_service.retry_run(run_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return RunView(
        id=run.id,
        status=run.status,
        metrics_summary=run.metrics_summary,
        error_reason=run.error_reason,
        artifacts=run.artifacts,
        project_id=run.project_id,
        config_id=run.config_id,
        dataset_id=run.dataset_id,
        retry_of=run.retry_of,
    )
