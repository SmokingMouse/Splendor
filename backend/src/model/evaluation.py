from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    id: str
    baseline_run_id: str
    candidate_run_id: str
    metrics: dict[str, float] = Field(default_factory=dict)
    conclusion: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
