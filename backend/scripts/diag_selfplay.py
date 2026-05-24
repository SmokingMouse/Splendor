"""Diagnostic: run N self-play games with a random-init network and report
termination + score statistics.

Run from backend dir:
    uv run python -m scripts.diag_selfplay --games 20 --max-moves 80 --mcts-sims 10
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from src.train.splendor_network import SplendorPVNet
from src.train.splendor_features import OBS_DIM
from src.train.splendor_selfplay import run_selfplay_game


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--max-moves", type=int, default=80)
    parser.add_argument("--mcts-sims", type=int, default=10)
    parser.add_argument("--temperature-moves", type=int, default=8)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--num-blocks", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    net = SplendorPVNet(obs_dim=OBS_DIM, hidden_dim=args.hidden_dim, num_blocks=args.num_blocks)
    net.eval()

    moves_list: list[int] = []
    natural_end = 0
    truncated = 0
    top_scores: list[int] = []
    all_scores: list[int] = []
    winners: list[str | None] = []

    t0 = time.time()
    for i in range(args.games):
        result = run_selfplay_game(
            network=net,
            mcts_iterations=args.mcts_sims,
            max_moves=args.max_moves,
            temperature_moves=args.temperature_moves,
            seed=args.seed + i,
            device=args.device,
        )
        moves_list.append(result.move_count)
        if result.reached_max_turns:
            truncated += 1
        else:
            natural_end += 1
        top_scores.append(max(result.final_scores))
        all_scores.extend(result.final_scores)
        winners.append(result.winner)
        print(
            f"  game {i:2d}: moves={result.move_count:3d} winner={result.winner} "
            f"scores={result.final_scores} truncated={result.reached_max_turns}"
        )
    elapsed = time.time() - t0

    print()
    print(f"=== {args.games} games in {elapsed:.1f}s ({elapsed / args.games:.1f}s/game) ===")
    print(f"natural end: {natural_end}/{args.games}  truncated: {truncated}/{args.games}")
    print(f"moves: mean={np.mean(moves_list):.1f}  min={min(moves_list)}  max={max(moves_list)}")
    print(f"top score per game: mean={np.mean(top_scores):.1f}  max={max(top_scores)}")
    print(f"all scores: mean={np.mean(all_scores):.1f}  >=15: {sum(s >= 15 for s in all_scores)}")


if __name__ == "__main__":
    main()
