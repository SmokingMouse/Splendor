from __future__ import annotations

from typing import Dict, List, Optional

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


MatchState.model_rebuild()
