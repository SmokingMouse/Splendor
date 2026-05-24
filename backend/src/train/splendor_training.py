from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..engine.ai_config import AiConfig, load_ai_configs
from ..infra.config import load_settings
from .splendor_policy import SplendorPolicyModel
from .splendor_selfplay import generate_teacher_samples


def _save_ai_config_entry(config_file: Path, model_path: Path) -> None:
    existing = load_ai_configs(config_file)
    out = []
    seen = False
    for cfg in existing:
        if cfg.id == "splendor-trained":
            out.append(
                {
                    "id": "splendor-trained",
                    "name": "璀璨宝石-训练策略",
                    "description": "基于自对弈教师信号训练的线性策略",
                    "path": str(model_path),
                }
            )
            seen = True
        else:
            out.append(
                {
                    "id": cfg.id,
                    "name": cfg.name,
                    "description": cfg.description,
                    "path": cfg.path,
                }
            )

    if not seen:
        out.append(
            {
                "id": "splendor-trained",
                "name": "璀璨宝石-训练策略",
                "description": "基于自对弈教师信号训练的线性策略",
                "path": str(model_path),
            }
        )

    payload = {"configs": out}
    config_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def run_training(episodes: int, epochs: int, lr: float, seed: int) -> dict[str, float]:
    settings = load_settings()
    model_path = settings.data_dir / "models" / "splendor_policy_latest.json"

    samples, sample_stats = generate_teacher_samples(episodes=episodes, seed=seed)
    model = SplendorPolicyModel.zeros()
    train_stats = model.train_rank_perceptron(samples=samples, epochs=epochs, lr=lr)
    model.save(model_path)
    _save_ai_config_entry(settings.ai_config_path, model_path)

    metrics = {
        **sample_stats,
        **train_stats,
    }
    metrics["model_path"] = str(model_path)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train baseline policy for Splendor AI")
    parser.add_argument("--episodes", type=int, default=80)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    metrics = run_training(
        episodes=args.episodes,
        epochs=args.epochs,
        lr=args.lr,
        seed=args.seed,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
