from __future__ import annotations

from pathlib import Path
import random
from typing import Optional

from .ai_config import load_ai_configs
from ..game.actions import Action
from ..game.legal_actions import generate_legal_actions
from ..game.state import MatchState
from ..infra.config import load_settings
from ..train.splendor_features import extract_action_features
from ..train.splendor_policy import SplendorPolicyModel

_MODEL_CACHE: dict[str, SplendorPolicyModel] = {}


def _resolve_model_path(ai_config_id: str) -> Path | None:
    settings = load_settings()
    for cfg in load_ai_configs(settings.ai_config_path):
        if cfg.id == ai_config_id and cfg.path:
            return Path(cfg.path)
    return None


def _select_with_model(state: MatchState, actions: list[Action], model_path: Path) -> Action:
    model_key = str(model_path)
    model = _MODEL_CACHE.get(model_key)
    if model is None:
        model = SplendorPolicyModel.load(model_path)
        _MODEL_CACHE[model_key] = model

    action_vectors = [extract_action_features(state, action).vector for action in actions]
    chosen_idx = model.choose_index(action_vectors)
    if chosen_idx < 0:
        return random.choice(actions)
    return actions[chosen_idx]


def select_ai_action(state: MatchState) -> Optional[Action]:
    actions = generate_legal_actions(state)
    if not actions:
        return None
    model_path = _resolve_model_path(state.ai_config_id)
    if model_path and model_path.exists():
        try:
            return _select_with_model(state, actions, model_path)
        except Exception:
            pass
    return random.choice(actions)
