from __future__ import annotations

import random
from typing import Optional

from ..game.actions import Action
from ..game.legal_actions import generate_legal_actions
from ..game.state import MatchState


def select_ai_action(state: MatchState) -> Optional[Action]:
    actions = generate_legal_actions(state)
    if not actions:
        return None
    return random.choice(actions)
