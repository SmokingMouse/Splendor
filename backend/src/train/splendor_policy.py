from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .splendor_features import FEATURE_NAMES


@dataclass
class SplendorPolicyModel:
    weights: np.ndarray

    @classmethod
    def zeros(cls) -> "SplendorPolicyModel":
        return cls(weights=np.zeros(len(FEATURE_NAMES), dtype=np.float32))

    def score(self, feature_vector: np.ndarray) -> float:
        return float(np.dot(self.weights, feature_vector))

    def choose_index(self, features: list[np.ndarray]) -> int:
        if not features:
            return -1
        scores = [self.score(vec) for vec in features]
        return int(np.argmax(scores))

    def train_rank_perceptron(
        self,
        samples: list[tuple[list[np.ndarray], int]],
        epochs: int = 8,
        lr: float = 0.05,
    ) -> dict[str, float]:
        updates = 0
        total = 0
        for _ in range(epochs):
            for feature_set, target_idx in samples:
                total += 1
                pred_idx = self.choose_index(feature_set)
                if pred_idx != target_idx:
                    self.weights += lr * (feature_set[target_idx] - feature_set[pred_idx])
                    updates += 1
        return {
            "samples": float(total),
            "updates": float(updates),
            "update_rate": float(updates / total) if total else 0.0,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "feature_names": FEATURE_NAMES,
            "weights": self.weights.tolist(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> "SplendorPolicyModel":
        payload = json.loads(path.read_text())
        weights = np.array(payload.get("weights", []), dtype=np.float32)
        if weights.shape[0] != len(FEATURE_NAMES):
            raise ValueError("Model feature dimension mismatch")
        return cls(weights=weights)
