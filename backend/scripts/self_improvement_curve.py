"""Pit each saved checkpoint against the one before it; export win-rate curve
as JSONL + simple console summary.

Self-improvement curve is AlphaZero's gold-standard evidence: if `step_N` beats
`step_(N-1)` with > 50% win rate consistently, the algorithm is learning. Flat
or downward → tuning needed.

Usage:
    uv run python -m scripts.self_improvement_curve \
        --ckpt-dir artifacts/checkpoints --games 24 --mcts-sims 25
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from src.train.splendor_agents import MCTSAgent
from src.train.splendor_evaluate import evaluate
from src.train.splendor_network import SplendorPVNet, load_checkpoint
from src.train.splendor_features import OBS_DIM

STEP_RE = re.compile(r"step_(\d+)\.pt$")


def list_step_ckpts(ckpt_dir: Path) -> list[Path]:
    paths = []
    for p in ckpt_dir.iterdir():
        m = STEP_RE.search(p.name)
        if m:
            paths.append((int(m.group(1)), p))
    paths.sort()
    return [p for _, p in paths]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt-dir", type=str, default="artifacts/checkpoints")
    parser.add_argument("--games", type=int, default=24)
    parser.add_argument("--max-moves", type=int, default=150)
    parser.add_argument("--mcts-sims", type=int, default=25)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--output", type=str, default="artifacts/self_improvement.jsonl")
    args = parser.parse_args()

    ckpt_dir = Path(args.ckpt_dir).resolve()
    ckpts = list_step_ckpts(ckpt_dir)
    if len(ckpts) < 2:
        raise SystemExit(f"need at least 2 step_*.pt in {ckpt_dir}, got {len(ckpts)}")

    print(f"Found {len(ckpts)} checkpoints:")
    for p in ckpts:
        print(f"  {p.name}")
    print()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for i in range(1, len(ckpts)):
        ckpt_a = ckpts[i]
        ckpt_b = ckpts[i - 1]

        net_a, _ = load_checkpoint(ckpt_a, device=args.device)
        net_a.eval()
        net_b, _ = load_checkpoint(ckpt_b, device=args.device)
        net_b.eval()

        agent_a = MCTSAgent(net_a, device=args.device, mcts_iterations=args.mcts_sims,
                            temperature=0.0, add_dirichlet=False, name=ckpt_a.stem)
        opponents = [
            MCTSAgent(net_b, device=args.device, mcts_iterations=args.mcts_sims,
                      temperature=0.0, add_dirichlet=False, name=ckpt_b.stem)
            for _ in range(3)
        ]

        t0 = time.time()
        result = evaluate(
            agent_a=agent_a,
            opponents=opponents,
            games=args.games,
            max_moves=args.max_moves,
            base_seed=i * 1000,
        )
        elapsed = time.time() - t0

        row = {
            "step_a": ckpt_a.stem,
            "step_b": ckpt_b.stem,
            "games": result.games,
            "win_rate": round(result.win_rate, 3),
            "natural_win_rate": round(result.natural_win_rate, 3),
            "score_a": round(result.a_score_mean, 2),
            "score_b": round(result.opp_score_mean, 2),
            "natural_games": result.natural_end_games,
            "truncated_games": result.truncated_games,
            "wall_seconds": round(elapsed, 1),
        }
        rows.append(row)
        print(
            f"{ckpt_a.stem} vs {ckpt_b.stem}: "
            f"win_rate={row['win_rate']:.2%} score={row['score_a']} vs {row['score_b']} "
            f"natural={row['natural_games']}/{row['games']} ({elapsed:.1f}s)"
        )

    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\n→ {output_path}")
    print()
    print("Verdict (heuristic): consistent win_rate > 50% means algorithm IS improving")
    win_rates = [r["win_rate"] for r in rows]
    avg = sum(win_rates) / max(1, len(win_rates))
    print(f"  avg win_rate across {len(rows)} matchups: {avg:.2%}")


if __name__ == "__main__":
    main()
