from __future__ import annotations

from fastapi import APIRouter

from ..errors import DomainError, as_http_exception
from ..schemas import DatasetCreate, DatasetView
from ...train.project_service import project_service

router = APIRouter()


@router.post("", response_model=DatasetView, status_code=201)
def create_dataset(payload: DatasetCreate) -> DatasetView:
    try:
        dataset = project_service.register_dataset(
            name=payload.name,
            source=payload.source,
            version=payload.version,
            schema_summary=payload.schema_summary,
        )
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return DatasetView(
        id=dataset.id,
        name=dataset.name,
        source=dataset.source,
        version=dataset.version,
        schema_summary=dataset.schema_summary,
        status=dataset.status,
    )
