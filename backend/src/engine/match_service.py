from __future__ import annotations

from typing import Dict

from ..game.actions import Action, ActionResult
from ..game.match import apply_and_advance, create_match
from ..game.state import MatchState
from ..infra.config import load_settings
from ..infra.storage import save_match_snapshot
from .ai_agent import select_ai_action
from ..game.legal_actions import generate_legal_actions

MATCHES: Dict[str, MatchState] = {}


def create_new_match(human_name: str, ai_config_id: str) -> MatchState:
    match = create_match(human_name, ai_config_id)
    MATCHES[match.id] = match
    return match


def get_match(match_id: str) -> MatchState | None:
    return MATCHES.get(match_id)


def persist_match(match: MatchState) -> None:
    settings = load_settings()
    save_match_snapshot(settings.data_dir, match)


def apply_player_action(match: MatchState, action: Action) -> ActionResult:
    result = apply_and_advance(match, action)
    if not result.success:
        return result

    if match.status == "running" and match.current_player_id.startswith("ai:"):
        ai_action = select_ai_action(match)
        if ai_action:
            apply_and_advance(match, ai_action)
        while match.return_tokens and match.current_player_id.startswith("ai:"):
            return_actions = [
                action
                for action in generate_legal_actions(match)
                if action.type == "return_gems"
            ]
            if not return_actions:
                break
            apply_and_advance(match, return_actions[0])

    if match.status == "finished":
        persist_match(match)

    return result
