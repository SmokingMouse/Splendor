from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch

from ..game.match import apply_and_advance, create_selfplay_match
from ..game.state import MatchState
from .splendor_action_space import ACTION_SPACE_SIZE
from .splendor_features import (
    NUM_PLAYERS,
    OBS_DIM,
    encode_observation,
    ranking_value_from_finished_state,
)
from .splendor_agents import HeuristicAgent
from .splendor_mcts import (
    DeterminizedMCTS,
    decode_to_action,
    sample_action_from_policy,
    visit_count_policy,
)
from .splendor_network import SplendorPVNet


@dataclass
class SelfPlaySample:
    obs: np.ndarray
    pi: np.ndarray
    value: np.ndarray
    player_id: str


@dataclass
class GameResult:
    samples: list[SelfPlaySample]
    final_scores: list[int]
    winner: Optional[str]
    turns: int
    move_count: int
    reached_max_turns: bool


def _force_return_gems_heuristic(state: MatchState) -> None:
    from ..game.legal_actions import generate_legal_actions

    while state.return_tokens:
        actions = generate_legal_actions(state)
        if not actions:
            break
        best_action = None
        best_score = -1
        for action in actions:
            if action.type != "return_gems":
                continue
            gems = action.payload.get("gems", {})
            score = sum(gems.values())
            if score > best_score:
                best_score = score
                best_action = action
        if best_action is None:
            best_action = actions[0]
        apply_and_advance(state, best_action)


def run_selfplay_game(
    network: SplendorPVNet,
    mcts_iterations: int = 50,
    max_moves: int = 120,
    temperature_moves: int = 16,
    seed: Optional[int] = None,
    device: str | torch.device = "cpu",
    c_puct: float = 1.5,
    dirichlet_alpha: float = 0.3,
    dirichlet_epsilon: float = 0.25,
    num_players: int = NUM_PLAYERS,
    add_dirichlet: bool = True,
    nn_seats: Optional[set[int]] = None,
) -> GameResult:
    """Run a single self-play game. By default all 4 seats are NN-controlled
    (pure self-play). Pass `nn_seats={0, 2}` etc. to make other seats run
    HeuristicAgent — only NN-controlled seats contribute training samples.
    Mixing heuristic opponents into a fraction of games is the v3 fix for
    AlphaZero pure-self-play bad equilibrium (NN-only sample never learn to
    buy cards → 0% vs heuristic baseline)."""
    rng = np.random.default_rng(seed)
    state = create_selfplay_match(num_players=num_players, prefix=f"sp{seed if seed is not None else 0}")

    if nn_seats is None:
        nn_seats = set(range(num_players))

    mcts = DeterminizedMCTS(
        network=network,
        device=device,
        c_puct=c_puct,
        dirichlet_alpha=dirichlet_alpha,
        dirichlet_epsilon=dirichlet_epsilon,
    )
    heuristic = HeuristicAgent()

    trajectory: list[tuple[np.ndarray, np.ndarray, str]] = []
    move_count = 0

    while state.status == "running" and move_count < max_moves:
        if state.return_tokens:
            _force_return_gems_heuristic(state)
            if state.status != "running":
                break
            continue

        current_player_id = state.current_player_id
        current_seat = next(i for i, p in enumerate(state.players) if p.id == current_player_id)

        if current_seat in nn_seats:
            obs = encode_observation(state, current_player_id)
            root, _ = mcts.run(state, iterations=mcts_iterations, add_dirichlet=add_dirichlet)
            if not root.children:
                break
            temperature = 1.0 if move_count < temperature_moves else 0.0
            pi = visit_count_policy(root, temperature=temperature)
            action_idx = sample_action_from_policy(pi, rng)
            if action_idx < 0:
                break
            action = decode_to_action(action_idx, state, current_player_id)
            if action is None:
                break
            trajectory.append((obs, pi, current_player_id))
        else:
            # Heuristic seat: just pick an action, no training sample
            action = heuristic.select_action(state, rng)
            if action is None:
                break

        apply_and_advance(state, action)
        move_count += 1

    reached_max = move_count >= max_moves and state.status == "running"
    final_scores = [p.score for p in state.players]

    samples: list[SelfPlaySample] = []
    for obs, pi, player_id in trajectory:
        value = ranking_value_from_finished_state(state, player_id)
        samples.append(SelfPlaySample(obs=obs, pi=pi, value=value, player_id=player_id))

    return GameResult(
        samples=samples,
        final_scores=final_scores,
        winner=state.winner,
        turns=state.turn,
        move_count=move_count,
        reached_max_turns=reached_max,
    )


def _pick_nn_seats(rng: np.random.Generator, num_players: int, heuristic_mix_rate: float) -> set[int]:
    """With probability `heuristic_mix_rate`, replace 1-3 seats with heuristic.
    Always keep at least 1 NN seat so training samples are non-empty."""
    if rng.random() >= heuristic_mix_rate:
        return set(range(num_players))
    num_heuristic = int(rng.integers(1, num_players))  # 1..num_players-1
    heuristic_seats = set(rng.choice(num_players, size=num_heuristic, replace=False).tolist())
    return set(range(num_players)) - heuristic_seats


def run_selfplay_batch(
    network: SplendorPVNet,
    num_games: int,
    mcts_iterations: int,
    max_moves: int,
    temperature_moves: int,
    base_seed: int,
    device: str | torch.device,
    heuristic_mix_rate: float = 0.0,
) -> list[GameResult]:
    """Self-play batch. `heuristic_mix_rate` ∈ [0, 1]: fraction of games where
    1-3 seats are replaced with HeuristicAgent (v3 anchor to escape pure
    self-play bad equilibrium)."""
    network.eval()
    seat_rng = np.random.default_rng(base_seed)
    results: list[GameResult] = []
    for game_idx in range(num_games):
        nn_seats = _pick_nn_seats(seat_rng, NUM_PLAYERS, heuristic_mix_rate)
        result = run_selfplay_game(
            network=network,
            mcts_iterations=mcts_iterations,
            max_moves=max_moves,
            temperature_moves=temperature_moves,
            seed=base_seed + game_idx,
            device=device,
            nn_seats=nn_seats,
        )
        results.append(result)
    return results
