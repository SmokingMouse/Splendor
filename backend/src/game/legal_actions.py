from __future__ import annotations

import hashlib
import itertools
import json
from typing import List

from .actions import Action
from .state import GEM_TYPES, MatchState, PlayerState


def generate_legal_actions(state: MatchState) -> List[Action]:
    if state.status != "running":
        return []

    player = _current_player(state)
    actions: List[Action] = []

    if _needs_return_gems(player):
        actions.extend(_return_gems_actions(state, player))
        return actions

    actions.extend(_take_gems_actions(state, player))
    actions.extend(_buy_card_actions(state, player))
    actions.extend(_reserve_card_actions(state, player))
    actions.extend(_reserve_deck_actions(state, player))

    return actions


def _current_player(state: MatchState) -> PlayerState:
    for player in state.players:
        if player.id == state.current_player_id:
            return player
    raise ValueError("player not found")


def _needs_return_gems(player: PlayerState) -> bool:
    return sum(player.gems.values()) > 10


def _return_gems_actions(state: MatchState, player: PlayerState) -> List[Action]:
    over = sum(player.gems.values()) - 10
    if over <= 0:
        return []
    actions: List[Action] = []

    gems = [gem for gem, count in player.gems.items() if count > 0]

    def backtrack(index: int, remaining: int, target: int, current: Dict[str, int]) -> None:
        if remaining == 0:
            payload = {"gems": dict(current)}
            actions.append(
                Action(
                    id=_stable_action_id("return_gems", payload, player.id),
                    type="return_gems",
                    player_id=player.id,
                    payload=payload,
                )
            )
            return
        if index >= len(gems):
            return
        gem = gems[index]
        max_take = min(player.gems[gem], remaining)
        for take in range(max_take + 1):
            if take > 0:
                current[gem] = take
            else:
                current.pop(gem, None)
            backtrack(index + 1, remaining - take, target, current)
            if len(actions) >= 50:
                return

    for target in range(1, over + 1):
        if len(actions) >= 50:
            break
        backtrack(0, target, target, {})
    if not actions:
        for gem in gems:
            payload = {"gems": {gem: 1}}
            actions.append(
                Action(
                    id=_stable_action_id("return_gems", payload, player.id),
                    type="return_gems",
                    player_id=player.id,
                    payload=payload,
                )
            )
    return actions


def _take_gems_actions(state: MatchState, player: PlayerState) -> List[Action]:
    actions: List[Action] = []
    available = {g: c for g, c in state.board.bank_gems.items() if g != "gold"}

    gems_with_stock = [g for g, c in available.items() if c > 0]
    if len(gems_with_stock) >= 3:
        for combo in itertools.combinations(gems_with_stock, 3):
            payload = {"gems": {combo[0]: 1, combo[1]: 1, combo[2]: 1}}
            actions.append(
                Action(
                    id=_stable_action_id("take_gems", payload, player.id),
                    type="take_gems",
                    player_id=player.id,
                    payload=payload,
                )
            )
    elif len(gems_with_stock) == 2:
        payload = {"gems": {gems_with_stock[0]: 1, gems_with_stock[1]: 1}}
        actions.append(
            Action(
                id=_stable_action_id("take_gems", payload, player.id),
                type="take_gems",
                player_id=player.id,
                payload=payload,
            )
        )
    elif len(gems_with_stock) == 1:
        payload = {"gems": {gems_with_stock[0]: 1}}
        actions.append(
            Action(
                id=_stable_action_id("take_gems", payload, player.id),
                type="take_gems",
                player_id=player.id,
                payload=payload,
            )
        )

    for gem, count in available.items():
        if count >= 4:
            payload = {"gems": {gem: 2}}
            actions.append(
                Action(
                    id=_stable_action_id("take_gems", payload, player.id),
                    type="take_gems",
                    player_id=player.id,
                    payload=payload,
                )
            )

    return actions


def _buy_card_actions(state: MatchState, player: PlayerState) -> List[Action]:
    actions: List[Action] = []
    for market in state.board.markets.values():
        for card in market:
            if card is None:
                continue
            payload = {"card_id": card.id}
            actions.append(
                Action(
                    id=_stable_action_id("buy_card", payload, player.id),
                    type="buy_card",
                    player_id=player.id,
                    payload=payload,
                )
            )
    for card in player.reserved:
        payload = {"card_id": card.id}
        actions.append(
            Action(
                id=_stable_action_id("buy_card", payload, player.id),
                type="buy_card",
                player_id=player.id,
                payload=payload,
            )
        )
    return actions


def _reserve_card_actions(state: MatchState, player: PlayerState) -> List[Action]:
    if len(player.reserved) >= 3:
        return []
    actions: List[Action] = []
    for market in state.board.markets.values():
        for card in market:
            if card is None:
                continue
            payload = {"card_id": card.id}
            actions.append(
                Action(
                    id=_stable_action_id("reserve_card", payload, player.id),
                    type="reserve_card",
                    player_id=player.id,
                    payload=payload,
                )
            )
    return actions


def _reserve_deck_actions(state: MatchState, player: PlayerState) -> List[Action]:
    if len(player.reserved) >= 3:
        return []
    actions: List[Action] = []
    for tier, deck in state.board.decks.items():
        if not deck:
            continue
        payload = {"tier": tier}
        actions.append(
            Action(
                id=_stable_action_id("reserve_deck", payload, player.id),
                type="reserve_deck",
                player_id=player.id,
                payload=payload,
            )
        )
    return actions


def _stable_action_id(action_type: str, payload: dict, player_id: str) -> str:
    content = json.dumps(
        {"type": action_type, "payload": payload, "player_id": player_id},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(content.encode("utf-8")).hexdigest()
