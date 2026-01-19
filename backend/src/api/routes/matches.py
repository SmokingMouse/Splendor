from __future__ import annotations

from fastapi import APIRouter

from ..errors import not_found
from ..schemas import CreateMatchRequest, MatchState, MatchSummary
from ...engine.match_service import create_new_match, get_match, persist_match
from .utils import to_state_view

router = APIRouter()


@router.post("", response_model=MatchSummary, status_code=201)
def create_match(payload: CreateMatchRequest) -> MatchSummary:
    match = create_new_match(payload.human_name, payload.ai_config_id)
    persist_match(match)
    return MatchSummary(id=match.id, status=match.status)


@router.get("/{match_id}", response_model=MatchState)
def get_match_state(match_id: str) -> MatchState:
    match = get_match(match_id)
    if not match:
        raise not_found("对局不存在")
    return to_state_view(match)
