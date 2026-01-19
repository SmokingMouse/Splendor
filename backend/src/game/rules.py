from __future__ import annotations

from typing import Optional

from .state import MatchState

WIN_SCORE = 15


def check_victory(state: MatchState) -> Optional[str]:
    top_score = -1
    winner = None
    for player in state.players:
        if player.score >= WIN_SCORE and player.score > top_score:
            top_score = player.score
            winner = player.id
    return winner
