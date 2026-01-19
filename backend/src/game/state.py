from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


GEM_TYPES = ["diamond", "sapphire", "emerald", "ruby", "onyx", "gold"]


def empty_gems() -> Dict[str, int]:
    return {gem: 0 for gem in GEM_TYPES}


@dataclass
class Card:
    id: str
    level: int
    points: int
    bonus: str
    cost: Dict[str, int]


@dataclass
class Noble:
    id: str
    points: int
    requirement: Dict[str, int]


@dataclass
class PlayerState:
    id: str
    type: str  # human | ai
    gems: Dict[str, int] = field(default_factory=empty_gems)
    cards: List[Card] = field(default_factory=list)
    reserved: List[Card] = field(default_factory=list)
    nobles: List[Noble] = field(default_factory=list)

    @property
    def score(self) -> int:
        return sum(card.points for card in self.cards) + sum(
            noble.points for noble in self.nobles
        )

    def bonus_counts(self) -> Dict[str, int]:
        bonus: Dict[str, int] = {gem: 0 for gem in GEM_TYPES}
        for card in self.cards:
            bonus[card.bonus] += 1
        return bonus


@dataclass
class BoardState:
    bank_gems: Dict[str, int]
    decks: Dict[int, List[Card]]
    markets: Dict[int, List[Card | None]]
    nobles: List[Noble]


@dataclass
class MatchState:
    id: str
    status: str  # created | running | finished
    current_player_id: str
    turn: int
    board: BoardState
    players: List[PlayerState]
    ai_config_id: str
    return_tokens: bool = False
    winner: Optional[str] = None
