from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class AiConfig:
    id: str
    name: str
    description: str
    path: str


def load_ai_configs(config_path: Path) -> List[AiConfig]:
    if not config_path.exists():
        return [
            AiConfig(
                id="default",
                name="默认 AI",
                description="占位 AI 配置",
                path="",
            )
        ]

    data = json.loads(config_path.read_text())
    configs = []
    for item in data.get("configs", []):
        configs.append(
            AiConfig(
                id=item["id"],
                name=item.get("name", item["id"]),
                description=item.get("description", ""),
                path=item.get("path", ""),
            )
        )
    return configs
