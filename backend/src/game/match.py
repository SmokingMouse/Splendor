from __future__ import annotations

import csv
import random
import uuid
from pathlib import Path
from typing import Dict, List

from .actions import Action, ActionResult, apply_action
from .rules import check_victory
from .state import BoardState, Card, MatchState, Noble, PlayerState, empty_gems

COLOR_ORDER = ["green", "white", "blue", "black", "red"]
COLOR_MAP: Dict[str, str] = {
    "green": "emerald",
    "white": "diamond",
    "blue": "sapphire",
    "black": "onyx",
    "red": "ruby",
}


def _load_cards() -> List[Card]:
    base_dir = Path(__file__).resolve().parents[3]
    csv_path = base_dir / "environment" / "cards.csv"
    cards: List[Card] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            tier = int(row["tier"])
            points = int(row["value"])
            bonus_index = int(row["type"]) - 1
            bonus_color = COLOR_ORDER[bonus_index]
            bonus = COLOR_MAP[bonus_color]

            cost: Dict[str, int] = {}
            for color in COLOR_ORDER:
                value = int(row[color])
                if value > 0:
                    cost[COLOR_MAP[color]] = value

            cards.append(
                Card(
                    id=f"t{tier}-{idx}",
                    level=tier,
                    points=points,
                    bonus=bonus,
                    cost=cost,
                )
            )
    return cards


def _load_nobles() -> List[Noble]:
    base_dir = Path(__file__).resolve().parents[3]
    csv_path = base_dir / "environment" / "nobles.csv"
    nobles: List[Noble] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            requirement: Dict[str, int] = {}
            for color in COLOR_ORDER:
                value = int(row[color])
                if value > 0:
                    requirement[COLOR_MAP[color]] = value
            nobles.append(Noble(id=f"n{idx}", points=3, requirement=requirement))
    return nobles


def _init_board() -> BoardState:
    bank = empty_gems()
    for gem in ["diamond", "sapphire", "emerald", "ruby", "onyx"]:
        bank[gem] = 4
    bank["gold"] = 5

    all_cards = _load_cards()
    decks: Dict[int, List[Card]] = {1: [], 2: [], 3: []}
    for card in all_cards:
        decks[card.level].append(card)

    for tier_cards in decks.values():
        random.shuffle(tier_cards)

    markets: Dict[int, List[Card | None]] = {1: [None] * 4, 2: [None] * 4, 3: [None] * 4}
    for tier in markets:
        _refill_market_from_deck(markets, decks, tier)

    nobles = _load_nobles()
    random.shuffle(nobles)
    nobles = nobles[:3]

    return BoardState(bank_gems=bank, decks=decks, markets=markets, nobles=nobles)


def _refill_market_from_deck(
    markets: Dict[int, List[Card | None]], decks: Dict[int, List[Card]], tier: int
) -> None:
    for index, card in enumerate(markets[tier]):
        if card is None and decks[tier]:
            markets[tier][index] = decks[tier].pop()


def create_match(human_name: str, ai_id: str) -> MatchState:
    match_id = str(uuid.uuid4())
    board = _init_board()
    players = [
        PlayerState(id=f"human:{human_name}", type="human"),
        PlayerState(id=f"ai:{ai_id}", type="ai"),
    ]
    return MatchState(
        id=match_id,
        status="running",
        current_player_id=players[0].id,
        turn=1,
        board=board,
        players=players,
        ai_config_id=ai_id,
    )


def apply_and_advance(state: MatchState, action: Action) -> ActionResult:
    result = apply_action(state, action)
    if not result.success:
        return result

    current_player = next(
        player for player in state.players if player.id == state.current_player_id
    )
    token_count = sum(current_player.gems.values())

    if action.type in ("take_gems", "reserve_card", "reserve_deck") and token_count > 10:
        state.return_tokens = True
        return result

    if action.type == "return_gems":
        if token_count <= 10:
            state.return_tokens = False
        else:
            return result

    winner = check_victory(state)
    if winner:
        state.status = "finished"
        state.winner = winner
        return result

    _advance_turn(state)
    return result


def _advance_turn(state: MatchState) -> None:
    ids = [player.id for player in state.players]
    current_index = ids.index(state.current_player_id)
    next_index = (current_index + 1) % len(ids)
    state.current_player_id = ids[next_index]
    state.turn += 1
