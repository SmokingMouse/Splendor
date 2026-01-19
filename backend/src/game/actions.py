from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .state import MatchState, PlayerState


@dataclass
class Action:
    id: str
    type: str
    player_id: str
    payload: Dict


@dataclass
class ActionResult:
    success: bool
    reason: Optional[str] = None


def validate_action(state: MatchState, action: Action) -> ActionResult:
    if state.status != "running":
        return ActionResult(False, "对局未处于进行中")
    if state.current_player_id != action.player_id:
        return ActionResult(False, "未轮到该玩家行动")
    if state.return_tokens and action.type != "return_gems":
        return ActionResult(False, "需要先归还宝石")
    return ActionResult(True)


def apply_action(state: MatchState, action: Action) -> ActionResult:
    validation = validate_action(state, action)
    if not validation.success:
        return validation

    if action.type == "take_gems":
        return _apply_take_gems(state, action)
    if action.type == "buy_card":
        return _apply_buy_card(state, action)
    if action.type == "reserve_card":
        return _apply_reserve_card(state, action)
    if action.type == "reserve_deck":
        return _apply_reserve_deck(state, action)
    if action.type == "return_gems":
        return _apply_return_gems(state, action)

    return ActionResult(False, "未知行动类型")


def _find_player(state: MatchState, player_id: str) -> PlayerState:
    for player in state.players:
        if player.id == player_id:
            return player
    raise ValueError("player not found")


def _apply_take_gems(state: MatchState, action: Action) -> ActionResult:
    payload = action.payload
    gems: Dict[str, int] = payload.get("gems", {})
    player = _find_player(state, action.player_id)

    for gem, count in gems.items():
        if state.board.bank_gems.get(gem, 0) < count:
            return ActionResult(False, f"宝石 {gem} 不足")

    for gem, count in gems.items():
        state.board.bank_gems[gem] -= count
        player.gems[gem] = player.gems.get(gem, 0) + count

    return ActionResult(True)


def _apply_buy_card(state: MatchState, action: Action) -> ActionResult:
    payload = action.payload
    card_id = payload.get("card_id")
    if not card_id:
        return ActionResult(False, "缺少 card_id")

    card, from_reserved, tier, slot_index = _find_card(state, action.player_id, card_id)
    if card is None:
        return ActionResult(False, "卡牌不存在")

    player = _find_player(state, action.player_id)
    bonus = player.bonus_counts()
    gold_available = player.gems.get("gold", 0)

    needed: Dict[str, int] = {}
    for gem, cost in card.cost.items():
        discount = min(bonus.get(gem, 0), cost)
        needed[gem] = max(cost - discount, 0)

    missing = 0
    for gem, need in needed.items():
        available = player.gems.get(gem, 0)
        if available < need:
            missing += need - available

    if missing > gold_available:
        return ActionResult(False, "资源不足")

    for gem, need in needed.items():
        pay = min(player.gems.get(gem, 0), need)
        if pay > 0:
            player.gems[gem] -= pay
            state.board.bank_gems[gem] += pay
        remaining = need - pay
        if remaining > 0:
            player.gems["gold"] -= remaining
            state.board.bank_gems["gold"] += remaining

    player.cards.append(card)
    if from_reserved:
        player.reserved.remove(card)
    else:
        if slot_index is not None:
            state.board.markets[tier][slot_index] = None
        _refill_market(state, tier)

    return ActionResult(True)


def _apply_reserve_card(state: MatchState, action: Action) -> ActionResult:
    payload = action.payload
    card_id = payload.get("card_id")
    card, _, tier, slot_index = _find_card(
        state, action.player_id, card_id, allow_reserved=False
    )
    if card is None:
        return ActionResult(False, "卡牌不存在")

    player = _find_player(state, action.player_id)
    if len(player.reserved) >= 3:
        return ActionResult(False, "预留卡牌已满")

    player.reserved.append(card)
    if slot_index is not None:
        state.board.markets[tier][slot_index] = None
    _refill_market(state, tier)

    if state.board.bank_gems.get("gold", 0) > 0:
        state.board.bank_gems["gold"] -= 1
        player.gems["gold"] = player.gems.get("gold", 0) + 1

    return ActionResult(True)


def _apply_reserve_deck(state: MatchState, action: Action) -> ActionResult:
    payload = action.payload
    tier = int(payload.get("tier", 0))
    if tier not in state.board.decks:
        return ActionResult(False, "无效牌堆等级")
    if not state.board.decks[tier]:
        return ActionResult(False, "牌堆已空")

    player = _find_player(state, action.player_id)
    if len(player.reserved) >= 3:
        return ActionResult(False, "预留卡牌已满")

    card = state.board.decks[tier].pop()
    player.reserved.append(card)

    if state.board.bank_gems.get("gold", 0) > 0:
        state.board.bank_gems["gold"] -= 1
        player.gems["gold"] = player.gems.get("gold", 0) + 1

    return ActionResult(True)


def _refill_market(state: MatchState, tier: int) -> None:
    for index, card in enumerate(state.board.markets[tier]):
        if card is None and state.board.decks[tier]:
            state.board.markets[tier][index] = state.board.decks[tier].pop()


def _find_card(
    state: MatchState, player_id: str, card_id: str, allow_reserved: bool = True
) -> tuple[object | None, bool, int, int | None]:
    for tier, market in state.board.markets.items():
        for index, card in enumerate(market):
            if card is not None and card.id == card_id:
                return card, False, tier, index

    if allow_reserved:
        player = _find_player(state, player_id)
        card = next((c for c in player.reserved if c.id == card_id), None)
        if card is not None:
            return card, True, card.level, None

    return None, False, -1, None


def _apply_return_gems(state: MatchState, action: Action) -> ActionResult:
    payload = action.payload
    gems: Dict[str, int] = payload.get("gems", {})
    player = _find_player(state, action.player_id)

    for gem, count in gems.items():
        if player.gems.get(gem, 0) < count:
            return ActionResult(False, f"宝石 {gem} 不足")

    for gem, count in gems.items():
        player.gems[gem] -= count
        state.board.bank_gems[gem] += count

    return ActionResult(True)
