from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import torch

from ..game.legal_actions import generate_legal_actions
from ..game.match import apply_and_advance
from ..game.rules import check_victory
from ..game.state import MatchState
from .splendor_action_space import (
    ACTION_SPACE_SIZE,
    decode_action,
    encode_action,
    legal_action_mask,
)
from .splendor_features import (
    NUM_PLAYERS,
    encode_observation,
    ranking_value_global,
)
from .splendor_network import SplendorPVNet


def _player_index(state: MatchState, player_id: str) -> int:
    for i, p in enumerate(state.players):
        if p.id == player_id:
            return i
    return 0


def _reshuffle_hidden_deck(state: MatchState) -> None:
    """Shuffle the unseen portion of each tier's deck. Visible markets and any
    reserved cards in players' hands stay put (those are public info). This is
    the minimum determinization to prevent NN learning to peek via
    reserve_deck."""
    rng = np.random.default_rng()
    for tier, deck in state.board.decks.items():
        if len(deck) > 1:
            indices = rng.permutation(len(deck))
            state.board.decks[tier] = [deck[i] for i in indices]


def _is_terminal(state: MatchState) -> bool:
    return state.status == "finished" or check_victory(state) is not None


@dataclass
class MCTSNode:
    state: MatchState
    perspective_idx: int
    parent: Optional["MCTSNode"] = None
    action_taken: Optional[int] = None
    prior_prob: float = 0.0
    visits: int = 0
    value_sum: np.ndarray = field(default_factory=lambda: np.zeros(NUM_PLAYERS, dtype=np.float32))
    children: dict[int, "MCTSNode"] = field(default_factory=dict)
    is_terminal: bool = False
    legal_mask: Optional[np.ndarray] = None

    def q_value(self, perspective_idx: int) -> float:
        if self.visits == 0:
            return 0.0
        return float(self.value_sum[perspective_idx] / self.visits)


class DeterminizedMCTS:
    def __init__(
        self,
        network: SplendorPVNet,
        device: str | torch.device = "cpu",
        c_puct: float = 1.5,
        dirichlet_alpha: float = 0.3,
        dirichlet_epsilon: float = 0.25,
    ) -> None:
        self.network = network
        self.device = device
        self.c_puct = c_puct
        self.dirichlet_alpha = dirichlet_alpha
        self.dirichlet_epsilon = dirichlet_epsilon

    @torch.no_grad()
    def _evaluate(self, state: MatchState) -> tuple[np.ndarray, np.ndarray]:
        perspective_idx = _player_index(state, state.current_player_id)
        perspective_id = state.players[perspective_idx].id
        obs = encode_observation(state, perspective_id)
        obs_t = torch.from_numpy(obs).unsqueeze(0).to(self.device)
        policy_logits, value_rotated = self.network(obs_t)
        policy_logits = policy_logits[0].cpu().numpy()
        value_rotated = value_rotated[0].cpu().numpy()
        num_players = len(state.players)
        value_global = np.zeros(NUM_PLAYERS, dtype=np.float32)
        for k in range(num_players):
            global_idx = (perspective_idx + k) % num_players
            value_global[global_idx] = value_rotated[k]
        return policy_logits, value_global

    def _expand(self, node: MCTSNode, policy_logits: np.ndarray) -> None:
        legal_actions = generate_legal_actions(node.state)
        mask = np.array(legal_action_mask(node.state, legal_actions), dtype=bool)
        node.legal_mask = mask

        if not mask.any():
            return

        logits_masked = np.where(mask, policy_logits, -1e8)
        logits_shift = logits_masked - logits_masked.max()
        exp = np.exp(logits_shift) * mask
        probs = exp / max(exp.sum(), 1e-12)

        for action in legal_actions:
            idx = encode_action(action, node.state)
            if idx is None or idx in node.children:
                continue
            child_state = deepcopy(node.state)
            apply_and_advance(child_state, action)
            child_terminal = _is_terminal(child_state)
            child = MCTSNode(
                state=child_state,
                perspective_idx=_player_index(child_state, child_state.current_player_id),
                parent=node,
                action_taken=idx,
                prior_prob=float(probs[idx]),
                is_terminal=child_terminal,
            )
            node.children[idx] = child

    def _select_child(self, node: MCTSNode) -> "MCTSNode":
        sqrt_parent = math.sqrt(max(node.visits, 1))
        best_score = -float("inf")
        best_child = None
        for child in node.children.values():
            q = child.q_value(node.perspective_idx)
            u = self.c_puct * child.prior_prob * sqrt_parent / (1 + child.visits)
            score = q + u
            if score > best_score:
                best_score = score
                best_child = child
        assert best_child is not None
        return best_child

    def _backup(self, node: MCTSNode, value: np.ndarray) -> None:
        current = node
        while current is not None:
            current.visits += 1
            current.value_sum += value
            current = current.parent

    def _apply_dirichlet(self, root: MCTSNode) -> None:
        if root.legal_mask is None or not root.children:
            return
        legal_indices = [idx for idx in root.children.keys()]
        noise = np.random.dirichlet([self.dirichlet_alpha] * len(legal_indices))
        for k, idx in enumerate(legal_indices):
            child = root.children[idx]
            child.prior_prob = (
                (1 - self.dirichlet_epsilon) * child.prior_prob
                + self.dirichlet_epsilon * float(noise[k])
            )

    def run(self, state: MatchState, iterations: int, add_dirichlet: bool = True) -> tuple[MCTSNode, np.ndarray]:
        # Re-shuffle hidden deck portion at the root so NN can't learn to peek
        # via reserve_deck. Without this, MCTS sees the real (visible to engine)
        # deck order and develops cheat-strategies (Session 2 v1: NN learned to
        # reserve tier-3 every turn → 0% vs heuristic).
        root_state = deepcopy(state)
        _reshuffle_hidden_deck(root_state)
        root = MCTSNode(
            state=root_state,
            perspective_idx=_player_index(state, state.current_player_id),
            is_terminal=_is_terminal(state),
        )

        if root.is_terminal:
            return root, ranking_value_global(state)

        policy_logits, value = self._evaluate(root.state)
        self._expand(root, policy_logits)
        if add_dirichlet:
            self._apply_dirichlet(root)
        self._backup(root, value)

        for _ in range(iterations):
            node = root
            while node.children and not node.is_terminal:
                node = self._select_child(node)

            if node.is_terminal:
                value = ranking_value_global(node.state)
            else:
                policy_logits, value = self._evaluate(node.state)
                self._expand(node, policy_logits)

            self._backup(node, value)

        return root, np.zeros(NUM_PLAYERS, dtype=np.float32)


def visit_count_policy(root: MCTSNode, temperature: float = 1.0) -> np.ndarray:
    pi = np.zeros(ACTION_SPACE_SIZE, dtype=np.float32)
    for idx, child in root.children.items():
        pi[idx] = float(child.visits)

    if temperature == 0:
        best_idx = int(np.argmax(pi))
        pi = np.zeros_like(pi)
        pi[best_idx] = 1.0
        return pi

    if temperature != 1.0:
        pi = np.power(pi, 1.0 / temperature)

    total = pi.sum()
    if total > 0:
        pi /= total
    return pi


def sample_action_from_policy(pi: np.ndarray, rng: np.random.Generator) -> int:
    if pi.sum() <= 0:
        return -1
    return int(rng.choice(len(pi), p=pi))


def decode_to_action(action_idx: int, state: MatchState, player_id: str):
    return decode_action(action_idx, state, player_id)
