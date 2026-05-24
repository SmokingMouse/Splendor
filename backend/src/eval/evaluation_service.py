from __future__ import annotations

from uuid import uuid4

from ..api.errors import domain_error
from ..model.evaluation import EvaluationResult
from ..train.repository import repo


class EvaluationService:
    def compare(self, baseline_run_id: str, candidate_run_id: str) -> EvaluationResult:
        if baseline_run_id == candidate_run_id:
            raise domain_error("INVALID_EVALUATION", "baseline_run_id and candidate_run_id must differ", 422)

        baseline = repo.get_run(baseline_run_id)
        candidate = repo.get_run(candidate_run_id)

        if baseline.status != "completed" or candidate.status != "completed":
            raise domain_error("RUN_NOT_COMPLETED", "Both runs must be completed for evaluation", 409)

        b_acc = float(baseline.metrics_summary.get("accuracy", 0.0))
        c_acc = float(candidate.metrics_summary.get("accuracy", 0.0))
        delta = round(c_acc - b_acc, 4)
        conclusion = (
            "candidate is better" if delta > 0 else "baseline remains better" if delta < 0 else "tie"
        )
        evaluation = EvaluationResult(
            id=f"eval-{uuid4().hex[:12]}",
            baseline_run_id=baseline.id,
            candidate_run_id=candidate.id,
            metrics={
                "baseline_accuracy": b_acc,
                "candidate_accuracy": c_acc,
                "delta_accuracy": delta,
            },
            conclusion=conclusion,
        )
        repo.save_evaluation(evaluation)
        return evaluation


evaluation_service = EvaluationService()
