from __future__ import annotations

from ..infra.config import load_settings
from .file_store import TrainingFileStore

settings = load_settings()
file_store = TrainingFileStore(settings.training_artifacts_dir, settings.max_artifact_bytes)
