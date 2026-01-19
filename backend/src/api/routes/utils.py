from __future__ import annotations

from ..schemas import MatchState, PlayerView


def to_state_view(match) -> MatchState:
    tiers = {}
    hidden = {}
    for tier, market in match.board.markets.items():
        slots = []
        for card in market:
            if card is None:
                slots.append(None)
            else:
                slots.append(
                    {
                        "id": card.id,
                        "points": card.points,
                        "bonus": card.bonus,
                        "cost": card.cost,
                        "tier": card.level,
                    }
                )
        tiers[str(tier)] = slots
        hidden[str(tier)] = len(match.board.decks[tier])

    board_state = {
        "bank_gems": match.board.bank_gems,
        "tiers": tiers,
        "hidden": hidden,
        "nobles": [
            {"id": noble.id, "points": noble.points, "requirement": noble.requirement}
            for noble in match.board.nobles
        ],
    }
    score = {player.id: player.score for player in match.players}
    players = [
        PlayerView(
            id=player.id,
            type=player.type,
            gems=player.gems,
            score=player.score,
            card_count=len(player.cards),
            reserved_cards=[
                {
                    "id": card.id,
                    "points": card.points,
                    "bonus": card.bonus,
                    "cost": card.cost,
                    "tier": card.level,
                }
                for card in player.reserved
            ],
            reserved_count=len(player.reserved),
            nobles_count=len(player.nobles),
            bonuses=player.bonus_counts(),
        )
        for player in match.players
    ]
    return MatchState(
        id=match.id,
        status=match.status,
        current_player_id=match.current_player_id,
        turn=match.turn,
        board_state=board_state,
        score=score,
        winner=match.winner,
        return_tokens=match.return_tokens,
        players=players,
    )
