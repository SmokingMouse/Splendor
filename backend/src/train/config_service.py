from __future__ import annotations

from uuid import uuid4

from ..api.errors import domain_error
from ..model.run import TrainingConfig
from .deps import file_store
from .repository import repo


class ConfigService:
    def create_config(
        self,
        project_id: str,
        name: str,
        parameters: dict,
        seed: int,
        *,
        parent_config_id: str | None = None,
    ) -> TrainingConfig:
        repo.get_project(project_id)
        if not name.strip():
            raise domain_error("INVALID_CONFIG", "Config name is required", 422)
        config = TrainingConfig(
            id=f"cfg-{uuid4().hex[:12]}",
            project_id=project_id,
            name=name,
            parameters=parameters,
            seed=seed,
            parent_config_id=parent_config_id,
        )
        repo.save_config(config)
        file_store.write_json(
            config.id,
            "config_snapshot.json",
            {
                "project_id": project_id,
                "name": name,
                "seed": seed,
                "parameters": parameters,
                "parent_config_id": parent_config_id,
            },
        )
        return config


config_service = ConfigService()
