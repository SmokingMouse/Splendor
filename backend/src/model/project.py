from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class TrainingProject(BaseModel):
    id: str
    name: str
    description: str = ""
    owner: str = "internal"
    dataset_ids: list[str] = Field(default_factory=list)
    latest_run_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["active", "archived"] = "active"


class Dataset(BaseModel):
    id: str
    name: str
    source: str
    version: str
    schema_summary: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["ready", "invalid"] = "ready"
