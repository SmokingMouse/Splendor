from __future__ import annotations

from fastapi import APIRouter

from ..errors import DomainError, as_http_exception
from ..schemas import EvaluationCreate, EvaluationView
from ...eval.evaluation_service import evaluation_service

router = APIRouter()


@router.post("/compare", response_model=EvaluationView)
def compare(payload: EvaluationCreate) -> EvaluationView:
    try:
        result = evaluation_service.compare(payload.baseline_run_id, payload.candidate_run_id)
    except DomainError as exc:
        raise as_http_exception(exc) from exc
    return EvaluationView(
        id=result.id,
        baseline_run_id=result.baseline_run_id,
        candidate_run_id=result.candidate_run_id,
        metrics=result.metrics,
        conclusion=result.conclusion,
        created_at=result.created_at,
    )
