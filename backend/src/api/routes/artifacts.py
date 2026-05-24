from __future__ import annotations

from fastapi import APIRouter

from ..errors import DomainError, as_http_exception
from ..schemas import ArtifactView
from ...train.run_service import run_service

router = APIRouter()


@router.get("/{artifact_id}", response_model=ArtifactView)
def get_artifact(artifact_id: str) -> ArtifactView:
    try:
        artifact = run_service.get_artifact(artifact_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return ArtifactView(
        id=artifact.id,
        run_id=artifact.run_id,
        type=artifact.type,
        uri=artifact.uri,
        checksum=artifact.checksum,
    )
