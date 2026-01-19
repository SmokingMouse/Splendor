from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..game.state import MatchState


def save_match_snapshot(base_dir: Path, match: MatchState) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"match-{match.id}.json"
    payload: dict[str, Any] = {
        "id": match.id,
        "status": match.status,
        "current_player_id": match.current_player_id,
        "turn": match.turn,
        "ai_config_id": match.ai_config_id,
        "winner": match.winner,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path
