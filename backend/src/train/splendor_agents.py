"""Agent abstractions used by self-play and evaluation.

Agents take a `MatchState` and return an `Action` (or None if no legal move).
This decouples evaluation from training: we can pit NN+MCTS vs random or
heuristic-greedy without rewriting MCTS internals.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Optional, Protocol

import numpy as np
import torch

from ..game.actions import Action
from ..game.legal_actions import generate_legal_actions
from ..game.state import MatchState
from .splendor_mcts import (
    DeterminizedMCTS,
    decode_to_action,
    sample_action_from_policy,
    visit_count_policy,
)
from .splendor_network import SplendorPVNet


class Agent(Protocol):
    name: str

    def select_action(self, state: MatchState, rng: np.random.Generator) -> Optional[Action]:
        ...


# ---------------------------------------------------------------------------
# Random
# ---------------------------------------------------------------------------


class RandomAgent:
    name = "random"

    def select_action(self, state: MatchState, rng: np.random.Generator) -> Optional[Action]:
        actions = generate_legal_actions(state)
        if not actions:
            return None
        return actions[rng.integers(len(actions))]


# ---------------------------------------------------------------------------
# Heuristic greedy
# ---------------------------------------------------------------------------


def _action_priority(action: Action, state: MatchState) -> tuple[int, float, float]:
    """Higher tuple = better. Categories (desc): buy > reserve_card_with_gold >
    take_3 > take_2 > reserve_card > reserve_deck > return_gems > others.
    Within category, prefer high-point cards, then cheap cards."""
    t = action.type
    payload = action.payload or {}
    if t == "buy_card" or t == "buy_reserved":
        card_id = payload.get("card_id")
        card = _lookup_card(card_id, state)
        points = float(card.points) if card else 0.0
        cost = float(sum((card.cost if card else {}).values()))
        return (100, points, -cost)
    if t == "reserve_card":
        card_id = payload.get("card_id")
        card = _lookup_card(card_id, state)
        points = float(card.points) if card else 0.0
        return (60, points, 0.0)
    if t == "take_gems":
        gems = payload.get("gems", {})
        count = sum(v for v in gems.values() if v > 0)
        distinct = sum(1 for v in gems.values() if v > 0)
        # take_3 > take_2
        return (50 if distinct >= 3 else (45 if distinct == 1 and count == 2 else 40), float(count), float(distinct))
    if t == "reserve_deck":
        return (30, 0.0, 0.0)
    if t == "return_gems":
        gems = payload.get("gems", {})
        # Prefer returning the fewest gems necessary
        return (20, -float(sum(gems.values())), 0.0)
    return (10, 0.0, 0.0)


def _lookup_card(card_id: Optional[str], state: MatchState):
    if not card_id:
        return None
    for tier_cards in state.board.markets.values():
        for c in tier_cards:
            if c is not None and c.id == card_id:
                return c
    for p in state.players:
        for c in p.reserved:
            if c.id == card_id:
                return c
    return None


class HeuristicAgent:
    name = "heuristic"

    def select_action(self, state: MatchState, rng: np.random.Generator) -> Optional[Action]:
        actions = generate_legal_actions(state)
        if not actions:
            return None
        scored = sorted(actions, key=lambda a: _action_priority(a, state), reverse=True)
        # Light tie-break to avoid deterministic loops: pick uniformly among top-3
        top = []
        best_key = _action_priority(scored[0], state)
        for a in scored:
            if _action_priority(a, state) == best_key:
                top.append(a)
            else:
                break
        return top[rng.integers(len(top))]


# ---------------------------------------------------------------------------
# NN + MCTS
# ---------------------------------------------------------------------------


class MCTSAgent:
    """Wraps a SplendorPVNet + DeterminizedMCTS for deterministic evaluation.

    Defaults: temperature=0 (argmax visit), no dirichlet noise. Override for
    self-play vs evaluation differences."""

    def __init__(
        self,
        network: SplendorPVNet,
        device: str | torch.device = "cpu",
        mcts_iterations: int = 50,
        c_puct: float = 1.5,
        temperature: float = 0.0,
        add_dirichlet: bool = False,
        name: str = "mcts",
    ) -> None:
        self.network = network
        self.device = device
        self.mcts_iterations = mcts_iterations
        self.temperature = temperature
        self.add_dirichlet = add_dirichlet
        self.name = name
        self._mcts = DeterminizedMCTS(
            network=network,
            device=device,
            c_puct=c_puct,
            dirichlet_alpha=0.3,
            dirichlet_epsilon=0.0 if not add_dirichlet else 0.25,
        )

    def select_action(self, state: MatchState, rng: np.random.Generator) -> Optional[Action]:
        # Defensive: never let MCTS mutate the source state
        local_state = deepcopy(state)
        root, _ = self._mcts.run(
            local_state,
            iterations=self.mcts_iterations,
            add_dirichlet=self.add_dirichlet,
        )
        if not root.children:
            return None
        pi = visit_count_policy(root, temperature=self.temperature)
        action_idx = sample_action_from_policy(pi, rng)
        if action_idx < 0:
            return None
        return decode_to_action(action_idx, state, state.current_player_id)
