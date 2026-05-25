"""Generate supervised training data from heuristic-vs-heuristic games.

Output: .npz with `obs` (N, OBS_DIM), `pi` (N, ACTION_SPACE_SIZE) one-hot,
`value` (N, NUM_PLAYERS) ranking values from the perspective of the acting
player.

Usage:
    uv run python -m scripts.generate_warmstart_data \
        --games 200 --max-moves 200 --output artifacts/warmstart_data.npz
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

from src.game.actions import Action
from src.game.match import apply_and_advance, create_selfplay_match
from src.game.state import MatchState
from src.train.splendor_action_space import ACTION_SPACE_SIZE, encode_action
from src.train.splendor_agents import HeuristicAgent
from src.train.splendor_features import (
    NUM_PLAYERS,
    OBS_DIM,
    encode_observation,
    final_value_from_state,
)
from src.train.splendor_selfplay import _force_return_gems_heuristic


def run_one_heuristic_game(
    seed: int, max_moves: int
) -> Tuple[List[np.ndarray], List[int], List[str], MatchState, int]:
    """Returns (obs_list, action_idx_list, player_id_list, final_state, move_count)."""
    rng = np.random.default_rng(seed)
    state = create_selfplay_match(num_players=NUM_PLAYERS, prefix=f"h{seed}")
    heuristic = HeuristicAgent()

    obs_list: list[np.ndarray] = []
    action_idx_list: list[int] = []
    player_id_list: list[str] = []
    move_count = 0

    while state.status == "running" and move_count < max_moves:
        if state.return_tokens:
            _force_return_gems_heuristic(state)
            if state.status != "running":
                break
            continue

        pid = state.current_player_id
        obs = encode_observation(state, pid)
        action: Action | None = heuristic.select_action(state, rng)
        if action is None:
            break

        idx = encode_action(action, state)
        if idx is None:
            # Skip uncodeable action (shouldn't happen for heuristic-chosen actions)
            apply_and_advance(state, action)
            move_count += 1
            continue

        obs_list.append(obs)
        action_idx_list.append(idx)
        player_id_list.append(pid)
        apply_and_advance(state, action)
        move_count += 1

    return obs_list, action_idx_list, player_id_list, state, move_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--max-moves", type=int, default=200)
    parser.add_argument("--output", type=str, default="artifacts/warmstart_data.npz")
    parser.add_argument("--seed-base", type=int, default=0)
    args = parser.parse_args()

    all_obs: list[np.ndarray] = []
    all_pi: list[np.ndarray] = []  # one-hot policy targets
    all_value: list[np.ndarray] = []  # rotated-perspective ranking values

    natural_end = 0
    move_totals: list[int] = []
    score_totals: list[int] = []
    t0 = time.time()

    for g in range(args.games):
        seed = args.seed_base + g
        obs_list, idx_list, pid_list, final_state, n_moves = run_one_heuristic_game(seed, args.max_moves)
        if final_state.winner is not None:
            natural_end += 1
        move_totals.append(n_moves)
        score_totals.extend(p.score for p in final_state.players)

        for obs, idx, pid in zip(obs_list, idx_list, pid_list):
            pi_one_hot = np.zeros(ACTION_SPACE_SIZE, dtype=np.float32)
            pi_one_hot[idx] = 1.0
            value = final_value_from_state(final_state, pid)

            all_obs.append(obs)
            all_pi.append(pi_one_hot)
            all_value.append(value)

        if (g + 1) % 20 == 0:
            print(
                f"  [{g + 1}/{args.games}] games, "
                f"{len(all_obs)} samples so far, "
                f"natural_end={natural_end}/{g + 1}, "
                f"avg_moves={np.mean(move_totals):.1f}"
            )

    elapsed = time.time() - t0
    obs_arr = np.stack(all_obs)
    pi_arr = np.stack(all_pi)
    value_arr = np.stack(all_value)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, obs=obs_arr, pi=pi_arr, value=value_arr)

    print()
    print(f"=== {args.games} heuristic games in {elapsed:.1f}s ===")
    print(f"  natural end: {natural_end}/{args.games} ({100 * natural_end / args.games:.0f}%)")
    print(f"  total samples: {len(all_obs)}")
    print(f"  avg moves/game: {np.mean(move_totals):.1f}")
    print(f"  score distribution: mean={np.mean(score_totals):.1f}, max={max(score_totals)}, >=15 count={sum(s >= 15 for s in score_totals)}")
    print(f"  saved to: {out_path}  (obs={obs_arr.shape}, pi={pi_arr.shape}, value={value_arr.shape})")


if __name__ == "__main__":
    main()
