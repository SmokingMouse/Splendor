from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..api.errors import domain_error


class TrainingFileStore:
    def __init__(self, base_dir: Path, max_artifact_bytes: int) -> None:
        self.base_dir = base_dir
        self.max_artifact_bytes = max_artifact_bytes
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        path = self.base_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, run_id: str, filename: str, payload: dict[str, Any]) -> str:
        out = self.run_dir(run_id) / filename
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return str(out)

    def write_log_line(self, run_id: str, message: str) -> str:
        out = self.run_dir(run_id) / "metrics.log"
        with out.open("a", encoding="utf-8") as fh:
            fh.write(message + "\n")
        return str(out)

    def write_artifact_placeholder(self, run_id: str, artifact_id: str) -> tuple[str, str]:
        out = self.run_dir(run_id) / f"{artifact_id}.json"
        payload = {"artifact_id": artifact_id, "run_id": run_id, "placeholder": True}
        serialized = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        if len(serialized) > self.max_artifact_bytes:
            raise domain_error("ARTIFACT_TOO_LARGE", "Artifact exceeds size limit", 413)
        out.write_bytes(serialized)
        checksum = hashlib.sha256(serialized).hexdigest()
        return str(out), checksum

    def enforce_limit(self) -> None:
        total = 0
        for path in self.base_dir.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        if total > self.max_artifact_bytes:
            raise domain_error("ARTIFACT_STORE_TOO_LARGE", "Artifacts directory exceeds configured limit", 413)
