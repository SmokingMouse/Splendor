"""Evaluation harness for Splendor AlphaZero.

Pits agent A (the candidate, typically NN+MCTS) against 3 opponent slots
(any mix of random / heuristic / another NN+MCTS checkpoint). Uses
**mixed seating**: A is rotated through all seats so seat order can't bias
the win rate.

Example:
    # candidate vs 3 random
    uv run python -m src.train.splendor_evaluate \
        --ckpt-a artifacts/checkpoints/latest.pt \
        --opponent random --games 24

    # candidate vs 3 heuristic
    uv run python -m src.train.splendor_evaluate \
        --ckpt-a artifacts/checkpoints/latest.pt \
        --opponent heuristic --games 24

    # candidate vs prior checkpoint (self-improvement curve)
    uv run python -m src.train.splendor_evaluate \
        --ckpt-a artifacts/checkpoints/step_000200.pt \
        --ckpt-b artifacts/checkpoints/step_000100.pt \
        --opponent ckpt --games 24
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from ..game.match import apply_and_advance, create_selfplay_match
from ..game.state import MatchState
from .splendor_agents import Agent, HeuristicAgent, MCTSAgent, RandomAgent
from .splendor_features import NUM_PLAYERS, OBS_DIM
from .splendor_network import SplendorPVNet, load_checkpoint
from .splendor_selfplay import _force_return_gems_heuristic


@dataclass
class GameOutcome:
    seat_of_a: int
    scores: list[int]
    winner_seat: Optional[int]
    move_count: int
    truncated: bool


@dataclass
class EvalResult:
    a_name: str
    opponent_name: str
    games: int
    a_wins: int
    a_natural_wins: int  # excluded truncated games
    a_score_mean: float
    opp_score_mean: float
    a_score_per_seat: list[float] = field(default_factory=list)
    truncated_games: int = 0
    natural_end_games: int = 0
    wall_seconds: float = 0.0

    @property
    def win_rate(self) -> float:
        return self.a_wins / max(1, self.games)

    @property
    def natural_win_rate(self) -> float:
        return self.a_natural_wins / max(1, self.natural_end_games)


def _winner_seat(state: MatchState, scores: list[int]) -> Optional[int]:
    """Return seat index of winner. If natural end, use state.winner; otherwise
    declare highest score as winner only if uncontested (no tie at top)."""
    if state.winner:
        for i, p in enumerate(state.players):
            if p.id == state.winner:
                return i
    # truncated: highest score wins; ties → no winner declared
    max_score = max(scores)
    leaders = [i for i, s in enumerate(scores) if s == max_score]
    if len(leaders) == 1:
        return leaders[0]
    return None


def _run_one_game(
    agents: list[Agent],
    seat_of_a: int,
    max_moves: int,
    seed: int,
) -> GameOutcome:
    rng = np.random.default_rng(seed)
    state = create_selfplay_match(num_players=NUM_PLAYERS, prefix=f"eval{seed}")
    move_count = 0

    while state.status == "running" and move_count < max_moves:
        if state.return_tokens:
            _force_return_gems_heuristic(state)
            if state.status != "running":
                break
            continue

        seat = next(i for i, p in enumerate(state.players) if p.id == state.current_player_id)
        agent = agents[seat]
        action = agent.select_action(state, rng)
        if action is None:
            break
        apply_and_advance(state, action)
        move_count += 1

    truncated = move_count >= max_moves and state.status == "running"
    scores = [p.score for p in state.players]
    return GameOutcome(
        seat_of_a=seat_of_a,
        scores=scores,
        winner_seat=_winner_seat(state, scores),
        move_count=move_count,
        truncated=truncated,
    )


def evaluate(
    agent_a: Agent,
    opponents: list[Agent],
    games: int = 24,
    max_moves: int = 120,
    base_seed: int = 0,
    verbose: bool = False,
) -> EvalResult:
    """`opponents` must contain (NUM_PLAYERS - 1) agents; A is rotated through
    all seats. `games` is rounded up to a multiple of NUM_PLAYERS."""
    assert len(opponents) == NUM_PLAYERS - 1, f"need {NUM_PLAYERS - 1} opponents"

    games_per_seat = max(1, games // NUM_PLAYERS)
    total_games = games_per_seat * NUM_PLAYERS

    a_wins = 0
    a_nat_wins = 0
    a_scores = []
    opp_scores = []
    a_score_per_seat = [[] for _ in range(NUM_PLAYERS)]
    truncated = 0
    natural = 0

    t0 = time.time()
    for seat_of_a in range(NUM_PLAYERS):
        # build the seating: A at seat_of_a, opponents fill the rest in given order
        agents: list[Agent] = []
        opp_iter = iter(opponents)
        for s in range(NUM_PLAYERS):
            if s == seat_of_a:
                agents.append(agent_a)
            else:
                agents.append(next(opp_iter))

        for g in range(games_per_seat):
            seed = base_seed + seat_of_a * 10_000 + g
            outcome = _run_one_game(agents, seat_of_a, max_moves, seed)
            a_score = outcome.scores[seat_of_a]
            a_scores.append(a_score)
            a_score_per_seat[seat_of_a].append(a_score)
            for i, s in enumerate(outcome.scores):
                if i != seat_of_a:
                    opp_scores.append(s)
            if outcome.truncated:
                truncated += 1
            else:
                natural += 1
            if outcome.winner_seat == seat_of_a:
                a_wins += 1
                if not outcome.truncated:
                    a_nat_wins += 1
            if verbose:
                print(
                    f"  seat={seat_of_a} g={g} scores={outcome.scores} "
                    f"winner_seat={outcome.winner_seat} trunc={outcome.truncated} "
                    f"moves={outcome.move_count}"
                )

    elapsed = time.time() - t0
    return EvalResult(
        a_name=agent_a.name,
        opponent_name=opponents[0].name + ("/" + opponents[1].name if opponents[1].name != opponents[0].name else ""),
        games=total_games,
        a_wins=a_wins,
        a_natural_wins=a_nat_wins,
        a_score_mean=float(np.mean(a_scores)) if a_scores else 0.0,
        opp_score_mean=float(np.mean(opp_scores)) if opp_scores else 0.0,
        a_score_per_seat=[float(np.mean(s)) if s else 0.0 for s in a_score_per_seat],
        truncated_games=truncated,
        natural_end_games=natural,
        wall_seconds=elapsed,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_mcts_agent(ckpt_path: str, device: str, mcts_sims: int, name: str) -> MCTSAgent:
    network = SplendorPVNet(obs_dim=OBS_DIM)
    network, metadata = load_checkpoint(Path(ckpt_path), device=device)
    network.eval()
    return MCTSAgent(
        network=network,
        device=device,
        mcts_iterations=mcts_sims,
        temperature=0.0,
        add_dirichlet=False,
        name=name,
    )


def _build_random_init_mcts(device: str, mcts_sims: int) -> MCTSAgent:
    network = SplendorPVNet(obs_dim=OBS_DIM)
    network.to(device)
    network.eval()
    return MCTSAgent(
        network=network,
        device=device,
        mcts_iterations=mcts_sims,
        temperature=0.0,
        add_dirichlet=False,
        name="random-init-mcts",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt-a", type=str, default=None, help="A: trained ckpt path (None = random-init MCTS)")
    parser.add_argument("--ckpt-b", type=str, default=None, help="B: prior ckpt for self-improvement curve")
    parser.add_argument(
        "--opponent",
        type=str,
        choices=["random", "heuristic", "ckpt", "random-init-mcts"],
        default="random",
    )
    parser.add_argument("--games", type=int, default=24)
    parser.add_argument("--max-moves", type=int, default=120)
    parser.add_argument("--mcts-sims", type=int, default=25)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--base-seed", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", help="print only json result")
    args = parser.parse_args()

    if args.ckpt_a:
        agent_a = _build_mcts_agent(args.ckpt_a, args.device, args.mcts_sims, name="A")
    else:
        agent_a = _build_random_init_mcts(args.device, args.mcts_sims)

    if args.opponent == "random":
        opponents: list[Agent] = [RandomAgent(), RandomAgent(), RandomAgent()]
    elif args.opponent == "heuristic":
        opponents = [HeuristicAgent(), HeuristicAgent(), HeuristicAgent()]
    elif args.opponent == "random-init-mcts":
        opponents = [_build_random_init_mcts(args.device, args.mcts_sims) for _ in range(3)]
    elif args.opponent == "ckpt":
        if not args.ckpt_b:
            raise SystemExit("--opponent ckpt requires --ckpt-b")
        opponents = [_build_mcts_agent(args.ckpt_b, args.device, args.mcts_sims, name="B") for _ in range(3)]
    else:
        raise SystemExit(f"unknown opponent: {args.opponent}")

    result = evaluate(
        agent_a=agent_a,
        opponents=opponents,
        games=args.games,
        max_moves=args.max_moves,
        base_seed=args.base_seed,
        verbose=args.verbose,
    )

    payload = {
        "a": result.a_name,
        "opponent": result.opponent_name,
        "games": result.games,
        "a_wins": result.a_wins,
        "win_rate": result.win_rate,
        "a_natural_wins": result.a_natural_wins,
        "natural_win_rate": round(result.natural_win_rate, 3),
        "a_score_mean": round(result.a_score_mean, 2),
        "opp_score_mean": round(result.opp_score_mean, 2),
        "a_score_per_seat": [round(s, 2) for s in result.a_score_per_seat],
        "truncated_games": result.truncated_games,
        "natural_end_games": result.natural_end_games,
        "wall_seconds": round(result.wall_seconds, 1),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print()
        print(f"=== {payload['a']} vs {payload['opponent']} ({payload['games']} games, {payload['wall_seconds']}s) ===")
        print(f"  win_rate: {payload['win_rate']:.2%}  ({payload['a_wins']}/{payload['games']})")
        print(f"  natural win_rate: {payload['natural_win_rate']:.2%}  (truncated={payload['truncated_games']})")
        print(f"  score: A={payload['a_score_mean']}  opp={payload['opp_score_mean']}")
        print(f"  A score per seat: {payload['a_score_per_seat']}")


if __name__ == "__main__":
    main()
