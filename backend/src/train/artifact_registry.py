from __future__ import annotations

from uuid import uuid4


def new_artifact_id(run_id: str) -> str:
    return f"artifact-{run_id}-{uuid4().hex[:8]}"
