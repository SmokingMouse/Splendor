from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from uuid import uuid4

from ..api.errors import domain_error
from ..model.run import Artifact, TrainingRun
from .artifact_registry import new_artifact_id
from .deps import file_store
from .project_service import project_service
from .repository import repo
from .runner import runner
from .status_machine import RunStatus, ensure_transition


class RunService:
    def start_run(self, project_id: str, config_id: str, dataset_id: str, retry_of: str | None = None) -> TrainingRun:
        project = repo.get_project(project_id)
        config = repo.get_config(config_id)
        dataset = repo.get_dataset(dataset_id)
        if dataset.id not in project.dataset_ids:
            raise domain_error("DATASET_NOT_IN_PROJECT", "Dataset is not linked to project", 422)
        if config.project_id != project.id:
            raise domain_error("CONFIG_PROJECT_MISMATCH", "Config does not belong to project", 422)

        run = TrainingRun(
            id=f"run-{uuid4().hex[:12]}",
            project_id=project_id,
            config_id=config_id,
            dataset_id=dataset_id,
            status=RunStatus.CREATED.value,
            retry_of=retry_of,
        )
        repo.save_run(run)
        self._set_status(run.id, RunStatus.QUEUED.value)
        runner.submit(lambda: self._execute_run(run.id))
        project_service.touch_project_run(project_id, run.id)
        return repo.get_run(run.id)

    def get_run(self, run_id: str) -> TrainingRun:
        return repo.get_run(run_id)

    def retry_run(self, run_id: str) -> TrainingRun:
        failed_run = repo.get_run(run_id)
        if failed_run.status not in {RunStatus.FAILED.value, RunStatus.CANCELED.value}:
            raise domain_error("RUN_NOT_RETRYABLE", "Only failed/canceled runs can be retried", 409)
        return self.start_run(
            project_id=failed_run.project_id,
            config_id=failed_run.config_id,
            dataset_id=failed_run.dataset_id,
            retry_of=failed_run.id,
        )

    def get_artifact(self, artifact_id: str) -> Artifact:
        return repo.get_artifact(artifact_id)

    def _set_status(self, run_id: str, target: str) -> None:
        run = repo.get_run(run_id)
        ensure_transition(run.status, target)
        run.status = target
        if target == RunStatus.RUNNING.value:
            run.started_at = datetime.now(timezone.utc)
        if target in {RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELED.value}:
            run.finished_at = datetime.now(timezone.utc)
        repo.save_run(run)

    def _execute_run(self, run_id: str) -> None:
        run = repo.get_run(run_id)
        try:
            self._set_status(run_id, RunStatus.RUNNING.value)
            rnd = random.Random(repo.get_config(run.config_id).seed)
            for step in range(1, 4):
                acc = round(0.55 + rnd.random() * 0.35 + step * 0.02, 4)
                loss = round(max(0.01, 1.2 - acc), 4)
                run.metrics_summary = {
                    "step": float(step),
                    "accuracy": acc,
                    "loss": loss,
                }
                repo.save_run(run)
                file_store.write_log_line(run.id, f"step={step},accuracy={acc},loss={loss}")
                time.sleep(0.05)
            artifact_id = new_artifact_id(run.id)
            uri, checksum = file_store.write_artifact_placeholder(run.id, artifact_id)
            artifact = Artifact(id=artifact_id, run_id=run.id, type="model", uri=uri, checksum=checksum)
            repo.save_artifact(artifact)
            run.artifacts = [artifact_id]
            repo.save_run(run)
            file_store.enforce_limit()
            self._set_status(run.id, RunStatus.COMPLETED.value)
        except Exception as exc:
            run = repo.get_run(run_id)
            if run.status == RunStatus.RUNNING.value:
                run.error_reason = str(exc)
                run.metrics_summary = run.metrics_summary or {"step": 0.0, "accuracy": 0.0, "loss": 0.0}
                repo.save_run(run)
                self._set_status(run.id, RunStatus.FAILED.value)


run_service = RunService()
