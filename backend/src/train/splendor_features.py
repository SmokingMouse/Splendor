from __future__ import annotations

import numpy as np

from ..game.state import Card, MatchState, Noble, PlayerState

GEM_COLORS = ["diamond", "sapphire", "emerald", "ruby", "onyx"]
GOLD = "gold"
TIERS = [1, 2, 3]
MARKET_SLOTS = 4
RESERVED_SLOTS = 3
NUM_NOBLES = 5
NUM_PLAYERS = 4

CARD_FEATURE_DIM = 12
NOBLE_FEATURE_DIM = 6
PLAYER_FEATURE_DIM = 48

OBS_DIM = (
    6
    + 3 * MARKET_SLOTS * CARD_FEATURE_DIM
    + 3
    + NUM_NOBLES * NOBLE_FEATURE_DIM
    + NUM_PLAYERS * PLAYER_FEATURE_DIM
    + 2
)
assert OBS_DIM == 377, f"unexpected OBS_DIM: {OBS_DIM}"


def _encode_card(card: Card | None) -> np.ndarray:
    vec = np.zeros(CARD_FEATURE_DIM, dtype=np.float32)
    if card is None:
        vec[5] = 1.0
        return vec
    if card.bonus in GEM_COLORS:
        vec[GEM_COLORS.index(card.bonus)] = 1.0
    vec[6] = float(card.points)
    for i, color in enumerate(GEM_COLORS):
        vec[7 + i] = float(card.cost.get(color, 0))
    return vec


def _encode_noble(noble: Noble | None) -> np.ndarray:
    vec = np.zeros(NOBLE_FEATURE_DIM, dtype=np.float32)
    if noble is None:
        return vec
    for i, color in enumerate(GEM_COLORS):
        vec[i] = float(noble.requirement.get(color, 0))
    vec[5] = float(noble.points)
    return vec


def _encode_player(player: PlayerState) -> np.ndarray:
    vec = np.zeros(PLAYER_FEATURE_DIM, dtype=np.float32)
    offset = 0
    for color in GEM_COLORS + [GOLD]:
        vec[offset] = float(player.gems.get(color, 0))
        offset += 1
    bonuses = player.bonus_counts()
    for color in GEM_COLORS:
        vec[offset] = float(bonuses.get(color, 0))
        offset += 1
    vec[offset] = float(player.score)
    offset += 1
    for slot in range(RESERVED_SLOTS):
        card = player.reserved[slot] if slot < len(player.reserved) else None
        vec[offset : offset + CARD_FEATURE_DIM] = _encode_card(card)
        offset += CARD_FEATURE_DIM
    assert offset == PLAYER_FEATURE_DIM
    return vec


def _rotated_players(state: MatchState, perspective_player_id: str) -> list[PlayerState]:
    ids = [p.id for p in state.players]
    if perspective_player_id not in ids:
        return list(state.players)
    start = ids.index(perspective_player_id)
    return [state.players[(start + i) % len(state.players)] for i in range(len(state.players))]


def encode_observation(state: MatchState, perspective_player_id: str) -> np.ndarray:
    parts: list[np.ndarray] = []

    bank = np.zeros(6, dtype=np.float32)
    for i, color in enumerate(GEM_COLORS + [GOLD]):
        bank[i] = float(state.board.bank_gems.get(color, 0))
    parts.append(bank)

    for tier in TIERS:
        market = state.board.markets.get(tier, [])
        for slot in range(MARKET_SLOTS):
            card = market[slot] if slot < len(market) else None
            parts.append(_encode_card(card))

    deck_counts = np.zeros(3, dtype=np.float32)
    for i, tier in enumerate(TIERS):
        deck_counts[i] = float(len(state.board.decks.get(tier, [])))
    parts.append(deck_counts)

    for slot in range(NUM_NOBLES):
        noble = state.board.nobles[slot] if slot < len(state.board.nobles) else None
        parts.append(_encode_noble(noble))

    rotated = _rotated_players(state, perspective_player_id)
    for slot in range(NUM_PLAYERS):
        if slot < len(rotated):
            parts.append(_encode_player(rotated[slot]))
        else:
            parts.append(np.zeros(PLAYER_FEATURE_DIM, dtype=np.float32))

    meta = np.array(
        [float(state.turn), 1.0 if state.return_tokens else 0.0],
        dtype=np.float32,
    )
    parts.append(meta)

    obs = np.concatenate(parts)
    assert obs.shape == (OBS_DIM,), f"obs shape {obs.shape} != ({OBS_DIM},)"
    return obs


def current_player_perspective_index(state: MatchState) -> int:
    ids = [p.id for p in state.players]
    if state.current_player_id in ids:
        return ids.index(state.current_player_id)
    return 0


_RANK_VALUE_TABLE = np.array([1.0, 0.33, -0.33, -1.0], dtype=np.float32)


def _score_to_rank_values(scores: np.ndarray) -> np.ndarray:
    """Convert scores to per-player ranking values. Ties share averaged value
    so player-order is never injected as signal (critical for truncated games
    where many players share score=0)."""
    n = scores.shape[0]
    rank_values = _RANK_VALUE_TABLE[:n]
    order = np.argsort(-scores, kind="stable")
    sorted_scores = scores[order]
    out = np.empty(n, dtype=np.float32)
    i = 0
    while i < n:
        j = i
        while j < n and sorted_scores[j] == sorted_scores[i]:
            j += 1
        avg = float(rank_values[i:j].mean())
        for k in range(i, j):
            out[order[k]] = avg
        i = j
    return out


def ranking_value_global(state: MatchState) -> np.ndarray:
    """4-d ranking value in **global** player order (state.players[0..3])."""
    scores = np.array([p.score for p in state.players], dtype=np.float32)
    return _score_to_rank_values(scores)


# Hybrid value: terminal game uses full ranking (±1 / ±0.33), truncated game uses
# a score-based fractional value capped at ±TRUNCATION_VALUE_SCALE. The cap is
# intentionally < 1 so that "winning a real game" stays a stronger signal than
# "ending a truncated game with the highest score". This unblocks AlphaZero
# from cold-starting in Splendor's sparse-reward 4-player setting (see
# decision log entry for 2026-05-25).
_WIN_SCORE = 15
TRUNCATION_VALUE_SCALE = 0.5
_TRUNCATION_NORM = 7.5  # = _WIN_SCORE * TRUNCATION_VALUE_SCALE

# Dense shaping: bonus per card owned at game end. Sessions 1-4 showed NN
# converging to "everyone reserves, no one buys" bad equilibrium in pure
# self-play (buy_card probability < 1% in v2). Adding a small per-card bonus
# to value targets makes "buy a card" globally better than "don't buy",
# even when the player loses, so the gradient anchors NN toward buying.
# Magnitude: heuristic typically owns 8-12 cards at game end → max bonus
# ~0.3-0.4, smaller than terminal win (1.0) but comparable to ranking rungs.
CARD_BUY_BONUS = 0.03


def _truncation_value_global(state: MatchState) -> np.ndarray:
    scores = np.array([p.score for p in state.players], dtype=np.float32)
    mean = float(scores.mean())
    centered = (scores - mean) / _TRUNCATION_NORM
    return np.clip(centered, -TRUNCATION_VALUE_SCALE, TRUNCATION_VALUE_SCALE).astype(np.float32)


def _rotate_to_perspective(values_global: np.ndarray, state: MatchState, perspective_player_id: str) -> np.ndarray:
    rotated_ids = [p.id for p in _rotated_players(state, perspective_player_id)]
    global_ids = [p.id for p in state.players]
    out = np.zeros_like(values_global)
    for i, pid in enumerate(rotated_ids):
        out[i] = values_global[global_ids.index(pid)]
    return out


def final_value_from_state(state: MatchState, perspective_player_id: str) -> np.ndarray:
    """4-d value in **rotated perspective** order. Hybrid: terminal uses ranking,
    non-terminal uses score-based fractional value with bounded magnitude.
    Plus CARD_BUY_BONUS per card owned (dense shaping to anchor "buy cards")."""
    if state.status == "finished" and state.winner is not None:
        values_global = ranking_value_global(state)
    else:
        values_global = _truncation_value_global(state)
    if CARD_BUY_BONUS > 0:
        card_bonus = np.array(
            [CARD_BUY_BONUS * len(p.cards) for p in state.players], dtype=np.float32
        )
        values_global = np.clip(values_global + card_bonus, -1.5, 1.5)
    return _rotate_to_perspective(values_global, state, perspective_player_id)


def ranking_value_from_finished_state(state: MatchState, perspective_player_id: str) -> np.ndarray:
    """Backwards-compatible alias — now routes to the hybrid value."""
    return final_value_from_state(state, perspective_player_id)
