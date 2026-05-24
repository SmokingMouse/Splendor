from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ..api.errors import domain_error
from ..model.project import Dataset, TrainingProject
from .repository import repo


class ProjectService:
    def create_project(self, name: str, dataset_ids: list[str], description: str = "") -> TrainingProject:
        if not name.strip():
            raise domain_error("INVALID_PROJECT", "Project name is required", 422)
        if not dataset_ids:
            raise domain_error("INVALID_PROJECT", "At least one dataset_id is required", 422)

        project = TrainingProject(
            id=f"proj-{uuid4().hex[:12]}",
            name=name,
            description=description,
            dataset_ids=dataset_ids,
        )
        return repo.save_project(project)

    def get_project(self, project_id: str) -> TrainingProject:
        return repo.get_project(project_id)

    def register_dataset(
        self, name: str, source: str, version: str, schema_summary: str = ""
    ) -> Dataset:
        if not source.strip() or not version.strip():
            raise domain_error("INVALID_DATASET", "source and version are required", 422)
        dataset = Dataset(
            id=f"ds-{uuid4().hex[:12]}",
            name=name,
            source=source,
            version=version,
            schema_summary=schema_summary,
        )
        return repo.save_dataset(dataset)

    def touch_project_run(self, project_id: str, run_id: str) -> None:
        project = repo.get_project(project_id)
        project.latest_run_id = run_id
        project.updated_at = datetime.now(timezone.utc)
        repo.save_project(project)


project_service = ProjectService()
