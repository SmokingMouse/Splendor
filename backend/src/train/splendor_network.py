from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from .splendor_action_space import ACTION_SPACE_SIZE
from .splendor_features import NUM_PLAYERS, OBS_DIM


class ResidualMLPBlock(nn.Module):
    def __init__(self, dim: int) -> None:
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.ln1 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.ln2 = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.fc1(x)
        h = self.ln1(h)
        h = F.relu(h)
        h = self.fc2(h)
        h = self.ln2(h)
        return F.relu(x + h)


class SplendorPVNet(nn.Module):
    def __init__(
        self,
        obs_dim: int = OBS_DIM,
        action_dim: int = ACTION_SPACE_SIZE,
        hidden_dim: int = 256,
        num_blocks: int = 2,
        value_dim: int = NUM_PLAYERS,
    ) -> None:
        super().__init__()
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.value_dim = value_dim

        self.input_proj = nn.Linear(obs_dim, hidden_dim)
        self.input_ln = nn.LayerNorm(hidden_dim)
        self.blocks = nn.ModuleList([ResidualMLPBlock(hidden_dim) for _ in range(num_blocks)])

        self.policy_head = nn.Linear(hidden_dim, action_dim)

        self.value_fc1 = nn.Linear(hidden_dim, 64)
        self.value_fc2 = nn.Linear(64, value_dim)

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.input_proj(obs)
        x = self.input_ln(x)
        x = F.relu(x)
        for block in self.blocks:
            x = block(x)
        policy_logits = self.policy_head(x)
        v = F.relu(self.value_fc1(x))
        value = torch.tanh(self.value_fc2(v))
        return policy_logits, value


def masked_log_softmax(logits: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    neg_inf = torch.full_like(logits, float("-inf"))
    masked = torch.where(mask, logits, neg_inf)
    return F.log_softmax(masked, dim=-1)


def save_checkpoint(model: SplendorPVNet, path: Path, metadata: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_state_dict": model.state_dict(),
        "config": {
            "obs_dim": model.obs_dim,
            "action_dim": model.action_dim,
            "hidden_dim": model.hidden_dim,
            "value_dim": model.value_dim,
        },
        "metadata": metadata or {},
    }
    torch.save(payload, path)


def load_checkpoint(path: Path, device: str | torch.device = "cpu") -> tuple[SplendorPVNet, dict]:
    payload = torch.load(path, map_location=device, weights_only=False)
    cfg = payload.get("config", {})
    model = SplendorPVNet(
        obs_dim=cfg.get("obs_dim", OBS_DIM),
        action_dim=cfg.get("action_dim", ACTION_SPACE_SIZE),
        hidden_dim=cfg.get("hidden_dim", 256),
        value_dim=cfg.get("value_dim", NUM_PLAYERS),
    )
    model.load_state_dict(payload["model_state_dict"])
    model.to(device)
    model.eval()
    return model, payload.get("metadata", {})


def write_checkpoint_index(checkpoints_dir: Path, name: str, path: Path, metrics: dict) -> Path:
    index = checkpoints_dir / "index.json"
    entries = []
    if index.exists():
        entries = json.loads(index.read_text()).get("entries", [])
    entries.append(
        {
            "name": name,
            "path": str(path.relative_to(checkpoints_dir.parent)),
            "metrics": metrics,
        }
    )
    index.write_text(json.dumps({"entries": entries}, indent=2))
    return index
