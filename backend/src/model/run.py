from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    id: str
    project_id: str
    name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    seed: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_default: bool = False
    parent_config_id: str | None = None


class Artifact(BaseModel):
    id: str
    run_id: str
    type: str
    uri: str
    checksum: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrainingRun(BaseModel):
    id: str
    project_id: str
    config_id: str
    dataset_id: str
    status: str = "created"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    metrics_summary: dict[str, float] = Field(default_factory=dict)
    logs_path: str = ""
    artifacts: list[str] = Field(default_factory=list)
    error_reason: str | None = None
    retry_of: str | None = None
