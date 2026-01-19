from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    data_dir: Path
    ai_config_path: Path


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[3]
    data_dir = base_dir / "backend" / "artifacts"
    ai_config_path = base_dir / "backend" / "ai_configs.json"
    return Settings(base_dir=base_dir, data_dir=data_dir, ai_config_path=ai_config_path)
