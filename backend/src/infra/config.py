from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    data_dir: Path
    ai_config_path: Path
    training_artifacts_dir: Path
    max_artifact_bytes: int


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[3]
    data_dir = base_dir / "backend" / "artifacts"
    ai_config_path = base_dir / "backend" / "ai_configs.json"
    training_artifacts_dir = data_dir / "training-runs"
    max_artifact_bytes = 5 * 1024 * 1024 * 1024
    return Settings(
        base_dir=base_dir,
        data_dir=data_dir,
        ai_config_path=ai_config_path,
        training_artifacts_dir=training_artifacts_dir,
        max_artifact_bytes=max_artifact_bytes,
    )
