from __future__ import annotations

from threading import RLock

from ..api.errors import domain_error
from ..model.evaluation import EvaluationResult
from ..model.project import Dataset, TrainingProject
from ..model.run import Artifact, TrainingConfig, TrainingRun


class InMemoryTrainingRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.projects: dict[str, TrainingProject] = {}
        self.datasets: dict[str, Dataset] = {}
        self.configs: dict[str, TrainingConfig] = {}
        self.runs: dict[str, TrainingRun] = {}
        self.artifacts: dict[str, Artifact] = {}
        self.evaluations: dict[str, EvaluationResult] = {}

    def save_project(self, project: TrainingProject) -> TrainingProject:
        with self._lock:
            self.projects[project.id] = project
            return project

    def get_project(self, project_id: str) -> TrainingProject:
        with self._lock:
            project = self.projects.get(project_id)
        if not project:
            raise domain_error("PROJECT_NOT_FOUND", f"Project not found: {project_id}", 404)
        return project

    def save_dataset(self, dataset: Dataset) -> Dataset:
        with self._lock:
            self.datasets[dataset.id] = dataset
            return dataset

    def get_dataset(self, dataset_id: str) -> Dataset:
        with self._lock:
            dataset = self.datasets.get(dataset_id)
        if not dataset:
            raise domain_error("DATASET_NOT_FOUND", f"Dataset not found: {dataset_id}", 404)
        return dataset

    def save_config(self, config: TrainingConfig) -> TrainingConfig:
        with self._lock:
            self.configs[config.id] = config
            return config

    def get_config(self, config_id: str) -> TrainingConfig:
        with self._lock:
            config = self.configs.get(config_id)
        if not config:
            raise domain_error("CONFIG_NOT_FOUND", f"Config not found: {config_id}", 404)
        return config

    def save_run(self, run: TrainingRun) -> TrainingRun:
        with self._lock:
            self.runs[run.id] = run
            return run

    def get_run(self, run_id: str) -> TrainingRun:
        with self._lock:
            run = self.runs.get(run_id)
        if not run:
            raise domain_error("RUN_NOT_FOUND", f"Run not found: {run_id}", 404)
        return run

    def save_artifact(self, artifact: Artifact) -> Artifact:
        with self._lock:
            self.artifacts[artifact.id] = artifact
            return artifact

    def get_artifact(self, artifact_id: str) -> Artifact:
        with self._lock:
            artifact = self.artifacts.get(artifact_id)
        if not artifact:
            raise domain_error("ARTIFACT_NOT_FOUND", f"Artifact not found: {artifact_id}", 404)
        return artifact

    def save_evaluation(self, evaluation: EvaluationResult) -> EvaluationResult:
        with self._lock:
            self.evaluations[evaluation.id] = evaluation
            return evaluation


repo = InMemoryTrainingRepository()
