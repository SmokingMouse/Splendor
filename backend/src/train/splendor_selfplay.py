from __future__ import annotations

import random

from ..game.legal_actions import generate_legal_actions
from ..game.match import apply_and_advance, create_match
from .splendor_features import extract_action_features


def _create_selfplay_match(seed: int, game_index: int):
    random.seed(seed + game_index)
    state = create_match(human_name=f"sp{game_index}", ai_id="default")
    state.players[0].id = f"ai:sp{game_index}:0"
    state.players[0].type = "ai"
    state.players[1].id = f"ai:sp{game_index}:1"
    state.players[1].type = "ai"
    state.current_player_id = state.players[0].id
    return state


def generate_teacher_samples(
    episodes: int,
    max_turns: int = 120,
    seed: int = 7,
) -> tuple[list[tuple[list, int]], dict[str, float]]:
    samples: list[tuple[list, int]] = []
    completed = 0

    for game_index in range(episodes):
        state = _create_selfplay_match(seed, game_index)

        while state.status == "running" and state.turn <= max_turns:
            actions = generate_legal_actions(state)
            if not actions:
                break
            features = [extract_action_features(state, action) for action in actions]
            teacher_idx = max(range(len(features)), key=lambda idx: features[idx].heuristic_value)
            feature_set = [item.vector for item in features]
            samples.append((feature_set, teacher_idx))
            apply_and_advance(state, actions[teacher_idx])

        if state.status == "finished":
            completed += 1

    stats = {
        "episodes": float(episodes),
        "completed_games": float(completed),
        "samples": float(len(samples)),
    }
    return samples, stats
