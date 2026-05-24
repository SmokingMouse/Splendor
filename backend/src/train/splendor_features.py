from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

import numpy as np

from ..game.actions import Action
from ..game.match import apply_and_advance
from ..game.state import GEM_TYPES, MatchState

FEATURE_NAMES = [
    "bias",
    "score_self",
    "score_opp",
    "score_gap",
    "gems_self_total",
    "gems_opp_total",
    "cards_self",
    "cards_opp",
    "reserved_self",
    "turn",
    "bank_diamond",
    "bank_sapphire",
    "bank_emerald",
    "bank_ruby",
    "bank_onyx",
    "bank_gold",
    "bonus_self_diamond",
    "bonus_self_sapphire",
    "bonus_self_emerald",
    "bonus_self_ruby",
    "bonus_self_onyx",
    "bonus_opp_diamond",
    "bonus_opp_sapphire",
    "bonus_opp_emerald",
    "bonus_opp_ruby",
    "bonus_opp_onyx",
]


@dataclass
class ActionFeatures:
    action: Action
    vector: np.ndarray
    heuristic_value: float


def _player_and_opponent(state: MatchState, player_id: str):
    player = next(p for p in state.players if p.id == player_id)
    opponent = next(p for p in state.players if p.id != player_id)
    return player, opponent


def state_vector(state: MatchState, player_id: str) -> np.ndarray:
    player, opponent = _player_and_opponent(state, player_id)
    bonuses_self = player.bonus_counts()
    bonuses_opp = opponent.bonus_counts()

    values = [
        1.0,
        float(player.score),
        float(opponent.score),
        float(player.score - opponent.score),
        float(sum(player.gems.values())),
        float(sum(opponent.gems.values())),
        float(len(player.cards)),
        float(len(opponent.cards)),
        float(len(player.reserved)),
        float(state.turn),
        float(state.board.bank_gems.get("diamond", 0)),
        float(state.board.bank_gems.get("sapphire", 0)),
        float(state.board.bank_gems.get("emerald", 0)),
        float(state.board.bank_gems.get("ruby", 0)),
        float(state.board.bank_gems.get("onyx", 0)),
        float(state.board.bank_gems.get("gold", 0)),
        float(bonuses_self.get("diamond", 0)),
        float(bonuses_self.get("sapphire", 0)),
        float(bonuses_self.get("emerald", 0)),
        float(bonuses_self.get("ruby", 0)),
        float(bonuses_self.get("onyx", 0)),
        float(bonuses_opp.get("diamond", 0)),
        float(bonuses_opp.get("sapphire", 0)),
        float(bonuses_opp.get("emerald", 0)),
        float(bonuses_opp.get("ruby", 0)),
        float(bonuses_opp.get("onyx", 0)),
    ]
    return np.array(values, dtype=np.float32)


def _heuristic_after_state(state: MatchState, player_id: str) -> float:
    player, opponent = _player_and_opponent(state, player_id)
    if state.status == "finished":
        if state.winner == player_id:
            return 10_000.0
        return -10_000.0

    gem_without_gold = sum(player.gems[g] for g in GEM_TYPES if g != "gold")
    bonus_total = sum(player.bonus_counts().values())
    return (
        player.score * 6.0
        - opponent.score * 4.0
        + len(player.cards) * 1.2
        - len(opponent.cards) * 0.8
        + bonus_total * 0.5
        + gem_without_gold * 0.1
        - len(player.reserved) * 0.2
    )


def extract_action_features(state: MatchState, action: Action) -> ActionFeatures:
    simulated = deepcopy(state)
    apply_and_advance(simulated, action)
    vector = state_vector(simulated, action.player_id)
    return ActionFeatures(action=action, vector=vector, heuristic_value=_heuristic_after_state(simulated, action.player_id))
