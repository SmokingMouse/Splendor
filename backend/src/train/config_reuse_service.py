from __future__ import annotations

from ..api.errors import domain_error
from .config_service import config_service
from .repository import repo


class ConfigReuseService:
    def reuse(self, project_id: str, config_id: str, name: str | None, parameters_override: dict | None, seed: int | None):
        base = repo.get_config(config_id)
        if base.project_id != project_id:
            raise domain_error("CONFIG_PROJECT_MISMATCH", "Config does not belong to project", 422)
        merged = dict(base.parameters)
        merged.update(parameters_override or {})
        return config_service.create_config(
            project_id=project_id,
            name=name or f"{base.name}-reuse",
            parameters=merged,
            seed=seed if seed is not None else base.seed,
            parent_config_id=base.id,
        )


config_reuse_service = ConfigReuseService()
