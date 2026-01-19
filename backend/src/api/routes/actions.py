from __future__ import annotations

from fastapi import APIRouter

from ..errors import bad_request, not_found
from ..schemas import ActionList, ActionResult, SubmitActionRequest
from ...engine.match_service import apply_player_action, get_match
from ...game.actions import Action as GameAction
from ...game.legal_actions import generate_legal_actions
from .utils import to_state_view

router = APIRouter()


@router.get("", response_model=ActionList)
def list_actions(match_id: str) -> ActionList:
    match = get_match(match_id)
    if not match:
        raise not_found("对局不存在")

    actions = generate_legal_actions(match)
    return ActionList(
        actions=[
            {"id": action.id, "type": action.type, "payload": action.payload}
            for action in actions
        ]
    )


@router.post("", response_model=ActionResult)
def submit_action(match_id: str, payload: SubmitActionRequest) -> ActionResult:
    match = get_match(match_id)
    if not match:
        raise not_found("对局不存在")

    legal_actions = generate_legal_actions(match)
    selected = next((a for a in legal_actions if a.id == payload.action_id), None)
    if not selected:
        if match.return_tokens and payload.payload.get("gems"):
            action = GameAction(
                id="return_gems",
                type="return_gems",
                player_id=match.current_player_id,
                payload=payload.payload,
            )
            result = apply_player_action(match, action)
            if not result.success:
                return ActionResult(
                    success=False, reason=result.reason, state=to_state_view(match)
                )
            return ActionResult(success=True, reason=None, state=to_state_view(match))
        raise bad_request("行动不可用")

    action = GameAction(
        id=selected.id,
        type=selected.type,
        player_id=match.current_player_id,
        payload={**selected.payload, **(payload.payload or {})},
    )

    result = apply_player_action(match, action)
    if not result.success:
        return ActionResult(success=False, reason=result.reason, state=to_state_view(match))

    return ActionResult(success=True, reason=None, state=to_state_view(match))
