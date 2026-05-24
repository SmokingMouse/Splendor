"""Regression tests for legal_actions.

The original failure: _buy_card_actions enumerated all market cards regardless
of player wallet, MCTS picked one, apply_action silently failed, seat never
advanced, and self-play stalled at 0 score forever.

Core invariant tested here: **every action returned by generate_legal_actions
must succeed when applied to the same state.**
"""

from __future__ import annotations

import random
from copy import deepcopy

import pytest

from src.game.actions import apply_action
from src.game.legal_actions import generate_legal_actions
from src.game.match import apply_and_advance, create_selfplay_match
from src.game.state import MatchState


def _fresh_state(seed: int, num_players: int = 4) -> MatchState:
    random.seed(seed)
    return create_selfplay_match(num_players=num_players, prefix=f"t{seed}")


def _every_legal_action_must_apply(state: MatchState, location: str) -> None:
    actions = generate_legal_actions(state)
    for a in actions:
        # apply on a deepcopy so we don't mutate the source state
        result = apply_action(deepcopy(state), a)
        assert result.success, (
            f"{location}: legal_action returned '{a.type}' (payload={a.payload}) "
            f"but apply_action rejected: {result.reason}. "
            f"Current player: {state.current_player_id}. "
            f"Player wallet: {[(p.gems, p.score) for p in state.players if p.id == state.current_player_id]}"
        )


def test_initial_state_all_legal_actions_apply():
    state = _fresh_state(seed=0)
    _every_legal_action_must_apply(state, "initial state")


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_random_walk_every_step_legal(seed: int):
    """Walk a random game; at each step every legal action must be applicable.
    Catches any state where legal_actions overpromises."""
    rng = random.Random(seed)
    state = _fresh_state(seed=seed)
    steps = 0
    while state.status == "running" and steps < 200:
        actions = generate_legal_actions(state)
        if not actions:
            break
        _every_legal_action_must_apply(state, f"seed={seed} step={steps}")
        chosen = rng.choice(actions)
        result = apply_and_advance(state, chosen)
        assert result.success, f"chosen action failed: {chosen} reason={result.reason}"
        steps += 1


def test_buy_card_only_when_affordable():
    """Specific regression: with empty wallet, no buy_card actions allowed."""
    state = _fresh_state(seed=42)
    actions = generate_legal_actions(state)
    buy_actions = [a for a in actions if a.type == "buy_card"]
    assert len(buy_actions) == 0, (
        f"Empty-wallet player should have 0 buy_card actions, got {len(buy_actions)}"
    )


def test_no_actions_when_finished():
    state = _fresh_state(seed=0)
    state.status = "finished"
    assert generate_legal_actions(state) == []
