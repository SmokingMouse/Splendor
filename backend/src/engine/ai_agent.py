"""AI agent dispatch for web-UI play.

The web UI passes an `ai_config_id` when creating a match. This module looks
that config up in `ai_configs.json`, picks the right backend agent (random
fallback, or PyTorch AlphaZero+MCTS), caches it across requests, and exposes
a single `select_ai_action(state)` entry point for `match_service`.

Failure mode: any error loading a checkpoint falls back to RandomAgent (logged
but not raised), so a broken AI config never bricks the web UI.
"""

from __future__ import annotations

import random
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from ..game.actions import Action
from ..game.legal_actions import generate_legal_actions
from ..game.state import MatchState
from ..infra.config import load_settings
from .ai_config import AiConfig, load_ai_configs


class _RandomFallbackAgent:
    name = "random-fallback"

    def select_action(self, state: MatchState, rng: np.random.Generator) -> Optional[Action]:
        actions = generate_legal_actions(state)
        if not actions:
            return None
        return actions[rng.integers(len(actions))]


_AGENT_CACHE: dict[str, object] = {}
_CACHE_LOCK = threading.Lock()
_DEFAULT_MCTS_SIMS = 30


def _build_agent_from_config(config: AiConfig):
    if not config.path:
        return _RandomFallbackAgent()

    path = Path(config.path)
    if not path.is_absolute():
        # resolve relative to repo root (backend/../<path>)
        path = (Path(__file__).resolve().parents[3] / config.path).resolve()

    if not path.exists():
        print(f"[ai_agent] config '{config.id}' path missing: {path}; falling back to random")
        return _RandomFallbackAgent()

    if path.suffix != ".pt":
        # legacy linear policy or unrecognized; fall back
        print(f"[ai_agent] config '{config.id}' path '{path}' not a .pt checkpoint; falling back to random")
        return _RandomFallbackAgent()

    # Lazy import torch so non-AI matches don't pay startup cost
    try:
        import torch  # noqa: F401
        from ..train.splendor_agents import MCTSAgent
        from ..train.splendor_network import load_checkpoint
    except ImportError as e:
        print(f"[ai_agent] torch/MCTS unavailable ({e}); falling back to random")
        return _RandomFallbackAgent()

    try:
        net, metadata = load_checkpoint(path, device="cpu")
        net.eval()
        mcts_sims = int(metadata.get("inference_mcts_sims", _DEFAULT_MCTS_SIMS))
        agent = MCTSAgent(
            network=net,
            device="cpu",
            mcts_iterations=mcts_sims,
            temperature=0.0,
            add_dirichlet=False,
            name=config.id,
        )
        print(f"[ai_agent] loaded '{config.id}' from {path} (mcts_sims={mcts_sims})")
        return agent
    except Exception as e:
        print(f"[ai_agent] failed to load checkpoint {path}: {e}; falling back to random")
        return _RandomFallbackAgent()


def _get_agent(ai_config_id: str):
    with _CACHE_LOCK:
        if ai_config_id in _AGENT_CACHE:
            return _AGENT_CACHE[ai_config_id]
        settings = load_settings()
        configs = load_ai_configs(settings.ai_config_path)
        config = next((c for c in configs if c.id == ai_config_id), None)
        if config is None:
            agent = _RandomFallbackAgent()
        else:
            agent = _build_agent_from_config(config)
        _AGENT_CACHE[ai_config_id] = agent
        return agent


def clear_agent_cache() -> None:
    """Drop cached agents — call this after registering a new checkpoint so
    next request picks up the new artifact without a server restart."""
    with _CACHE_LOCK:
        _AGENT_CACHE.clear()


def select_ai_action(state: MatchState) -> Optional[Action]:
    actions = generate_legal_actions(state)
    if not actions:
        return None
    config_id = state.ai_config_id or "default"
    agent = _get_agent(config_id)
    rng = np.random.default_rng()
    try:
        return agent.select_action(state, rng)
    except Exception as e:
        print(f"[ai_agent] agent '{config_id}' raised ({e}); falling back to random action")
        return random.choice(actions)
