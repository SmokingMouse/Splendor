from __future__ import annotations

import itertools
from typing import Optional

from ..game.actions import Action
from ..game.legal_actions import _stable_action_id
from ..game.state import MatchState

GEM_COLORS = ["diamond", "sapphire", "emerald", "ruby", "onyx"]
TIERS = [1, 2, 3]
MARKET_SLOTS = 4
RESERVED_SLOTS = 3

ACTION_SPACE_SIZE = 60


def _take_gems_key(gems: dict) -> frozenset:
    return frozenset((g, c) for g, c in gems.items() if c > 0)


def _build_index_to_spec() -> tuple[list[tuple[str, dict]], dict[frozenset, int]]:
    specs: list[tuple[str, dict]] = []
    take_lookup: dict[frozenset, int] = {}

    def add_take(gems: dict) -> None:
        specs.append(("take_gems", {"gems": gems}))
        take_lookup[_take_gems_key(gems)] = len(specs) - 1

    for combo in itertools.combinations(GEM_COLORS, 3):
        add_take({g: 1 for g in combo})

    for gem in GEM_COLORS:
        add_take({gem: 2})

    for combo in itertools.combinations(GEM_COLORS, 2):
        add_take({combo[0]: 1, combo[1]: 1})

    for gem in GEM_COLORS:
        add_take({gem: 1})

    for tier in TIERS:
        for slot in range(MARKET_SLOTS):
            specs.append(("buy_card", {"source": "market", "tier": tier, "slot": slot}))

    for slot in range(RESERVED_SLOTS):
        specs.append(("buy_card", {"source": "reserved", "slot": slot}))

    for tier in TIERS:
        for slot in range(MARKET_SLOTS):
            specs.append(("reserve_card", {"source": "market", "tier": tier, "slot": slot}))

    for tier in TIERS:
        specs.append(("reserve_deck", {"tier": tier}))

    assert len(specs) == ACTION_SPACE_SIZE, f"action space size mismatch: {len(specs)}"
    return specs, take_lookup


INDEX_TO_SPEC, TAKE_GEMS_LOOKUP = _build_index_to_spec()


def _take_gems_index(payload: dict) -> Optional[int]:
    gems = payload.get("gems", {})
    return TAKE_GEMS_LOOKUP.get(_take_gems_key(gems))


def _resolve_card_market_slot(state: MatchState, card_id: str) -> Optional[tuple[int, int]]:
    for tier, market in state.board.markets.items():
        for slot, card in enumerate(market):
            if card is not None and card.id == card_id:
                return (tier, slot)
    return None


def _resolve_card_reserved_slot(state: MatchState, card_id: str, player_id: str) -> Optional[int]:
    player = next(p for p in state.players if p.id == player_id)
    for slot, card in enumerate(player.reserved):
        if card.id == card_id:
            return slot
    return None


def encode_action(action: Action, state: MatchState) -> Optional[int]:
    if action.type == "take_gems":
        return _take_gems_index(action.payload)

    if action.type == "buy_card":
        card_id = action.payload.get("card_id")
        if card_id is None:
            return None
        market_slot = _resolve_card_market_slot(state, card_id)
        if market_slot is not None:
            tier, slot = market_slot
            return 30 + (tier - 1) * MARKET_SLOTS + slot
        reserved_slot = _resolve_card_reserved_slot(state, card_id, action.player_id)
        if reserved_slot is not None:
            return 42 + reserved_slot
        return None

    if action.type == "reserve_card":
        card_id = action.payload.get("card_id")
        market_slot = _resolve_card_market_slot(state, card_id) if card_id else None
        if market_slot is not None:
            tier, slot = market_slot
            return 45 + (tier - 1) * MARKET_SLOTS + slot
        return None

    if action.type == "reserve_deck":
        tier = action.payload.get("tier")
        if tier in TIERS:
            return 57 + (tier - 1)
        return None

    return None


def decode_action(index: int, state: MatchState, player_id: str) -> Optional[Action]:
    if not (0 <= index < ACTION_SPACE_SIZE):
        return None

    action_type, spec = INDEX_TO_SPEC[index]

    if action_type == "take_gems":
        payload = {"gems": dict(spec["gems"])}
        return Action(
            id=_stable_action_id("take_gems", payload, player_id),
            type="take_gems",
            player_id=player_id,
            payload=payload,
        )

    if action_type == "buy_card":
        if spec["source"] == "market":
            tier, slot = spec["tier"], spec["slot"]
            market = state.board.markets.get(tier, [])
            if slot >= len(market) or market[slot] is None:
                return None
            payload = {"card_id": market[slot].id}
        else:
            player = next(p for p in state.players if p.id == player_id)
            slot = spec["slot"]
            if slot >= len(player.reserved):
                return None
            payload = {"card_id": player.reserved[slot].id}
        return Action(
            id=_stable_action_id("buy_card", payload, player_id),
            type="buy_card",
            player_id=player_id,
            payload=payload,
        )

    if action_type == "reserve_card":
        tier, slot = spec["tier"], spec["slot"]
        market = state.board.markets.get(tier, [])
        if slot >= len(market) or market[slot] is None:
            return None
        payload = {"card_id": market[slot].id}
        return Action(
            id=_stable_action_id("reserve_card", payload, player_id),
            type="reserve_card",
            player_id=player_id,
            payload=payload,
        )

    if action_type == "reserve_deck":
        tier = spec["tier"]
        if not state.board.decks.get(tier):
            return None
        payload = {"tier": tier}
        return Action(
            id=_stable_action_id("reserve_deck", payload, player_id),
            type="reserve_deck",
            player_id=player_id,
            payload=payload,
        )

    return None


def legal_action_mask(state: MatchState, legal_actions: list[Action]) -> list[bool]:
    mask = [False] * ACTION_SPACE_SIZE
    for action in legal_actions:
        idx = encode_action(action, state)
        if idx is not None:
            mask[idx] = True
    return mask
