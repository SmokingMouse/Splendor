from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateMatchRequest(BaseModel):
    human_name: str
    ai_config_id: str


class MatchSummary(BaseModel):
    id: str
    status: str


class MatchState(BaseModel):
    id: str
    status: str
    current_player_id: str
    turn: int
    board_state: Dict
    score: Dict[str, int]
    winner: Optional[str] = None
    players: list["PlayerView"]
    return_tokens: bool = False


class Action(BaseModel):
    id: str
    type: str
    payload: Dict


class ActionList(BaseModel):
    actions: List[Action]


class SubmitActionRequest(BaseModel):
    action_id: str
    payload: Dict = Field(default_factory=dict)


class ActionResult(BaseModel):
    success: bool
    reason: Optional[str] = None
    state: MatchState


class AiConfig(BaseModel):
    id: str
    name: str
    description: str


class AiConfigList(BaseModel):
    configs: List[AiConfig]


class PlayerView(BaseModel):
    id: str
    type: str
    gems: Dict[str, int]
    score: int
    card_count: int
    reserved_cards: List[Dict]
    reserved_count: int
    nobles_count: int
    bonuses: Dict[str, int]


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    dataset_ids: list[str] = Field(default_factory=list)


class ProjectView(BaseModel):
    id: str
    name: str
    description: str
    dataset_ids: list[str]
    status: str
    latest_run_id: str | None = None


class DatasetCreate(BaseModel):
    name: str
    source: str
    version: str
    schema_summary: str = ""


class DatasetView(BaseModel):
    id: str
    name: str
    source: str
    version: str
    schema_summary: str
    status: str


class ConfigCreate(BaseModel):
    name: str
    parameters: dict[str, Any]
    seed: int


class ConfigReuseRequest(BaseModel):
    name: str | None = None
    parameters_override: dict[str, Any] = Field(default_factory=dict)
    seed: int | None = None


class ConfigView(BaseModel):
    id: str
    project_id: str
    name: str
    parameters: dict[str, Any]
    seed: int
    parent_config_id: str | None = None


class RunCreate(BaseModel):
    config_id: str
    dataset_id: str


class RunView(BaseModel):
    id: str
    status: str
    metrics_summary: dict[str, float]
    error_reason: str | None
    artifacts: list[str]
    project_id: str
    config_id: str
    dataset_id: str
    retry_of: str | None = None


class ArtifactView(BaseModel):
    id: str
    run_id: str
    type: str
    uri: str
    checksum: str | None


class EvaluationCreate(BaseModel):
    baseline_run_id: str
    candidate_run_id: str


class EvaluationView(BaseModel):
    id: str
    baseline_run_id: str
    candidate_run_id: str
    metrics: dict[str, float]
    conclusion: str
    created_at: datetime


if hasattr(MatchState, "model_rebuild"):
    MatchState.model_rebuild()
else:
    MatchState.update_forward_refs()
