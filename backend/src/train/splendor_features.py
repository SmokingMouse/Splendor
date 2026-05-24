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


def ranking_value_from_finished_state(state: MatchState, perspective_player_id: str) -> np.ndarray:
    rotated_ids = [p.id for p in _rotated_players(state, perspective_player_id)]
    rotated_scores = np.array(
        [next(p.score for p in state.players if p.id == pid) for pid in rotated_ids],
        dtype=np.float32,
    )
    order = np.argsort(-rotated_scores, kind="stable")
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(order))
    rank_values = np.array([1.0, 0.33, -0.33, -1.0], dtype=np.float32)
    return rank_values[ranks]
