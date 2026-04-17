from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from entrypoints.run_archive import write_run_archive


ARCHIVE_ROOT = REPO_ROOT / "paper" / "data" / "case_study_archives" / "case_b_rag"
WORKFLOW_PROFILE_ID = "paper_case_b_rag"


def build_surface_request(task: str) -> dict:
    return {
        "task": task,
        "task_type": "rag",
        "workflow_profile_id": WORKFLOW_PROFILE_ID,
    }


def build_success_result() -> dict:
    return {
        "surface": {"workflow_profile_id": WORKFLOW_PROFILE_ID},
        "task_contract": {
            "goal": "Answer a factual question with retrieved supporting snippets.",
            "task_type": "rag",
            "task_id": "case-b-success",
            "contract_id": "case-b-success-contract",
            "workflow_profile_id": WORKFLOW_PROFILE_ID,
            "success_criteria": ["Answer is grounded in retrieved snippets."],
            "expected_artifacts": ["answer", "retrieval_report"],
        },
        "execution_result": {
            "status": "success",
            "tool_name": "paper_rag_agent",
            "output": "Archive-first-harness is positioned as an Evidence Layer in the AI agent stack.",
            "artifacts": [
                {"type": "answer", "path": "case_b/success_answer.md"},
                {"type": "retrieval_report", "path": "case_b/success_retrieval.json"},
            ],
            "metadata": {"retrieval_strategy": "targeted", "top_k": 3},
        },
        "verification_report": {
            "passed": True,
            "status": "passed",
            "warnings": [],
        },
        "metrics_summary": {"retrieval_hits": 3, "duration_ms": 1400},
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": WORKFLOW_PROFILE_ID,
                "task_type": "rag",
            }
        },
        "realm_evaluation": {
            "status": "pass",
            "recommendation": "keep",
            "requires_human_review": False,
            "reason_codes": ["grounded_answer", "sufficient_retrieval"],
            "metadata": {"automatic_action": "none"},
        },
        "baseline_compare_results": {
            "status": "completed",
            "compared_artifact_types": ["answer", "retrieval_report"],
            "status_counts": {"compatible": 2},
        },
        "residual_followup": {
            "auto_execution": "none",
            "reassessment": {
                "reassessed_level": "low",
                "needs_followup": False,
                "reason_codes": ["grounding_confirmed"],
            },
            "governance": {"status": "clear", "requires_governance_override": False},
        },
    }


def build_failure_result() -> dict:
    return {
        "surface": {"workflow_profile_id": WORKFLOW_PROFILE_ID},
        "task_contract": {
            "goal": "Answer a factual question with retrieved supporting snippets.",
            "task_type": "rag",
            "task_id": "case-b-failure",
            "contract_id": "case-b-failure-contract",
            "workflow_profile_id": WORKFLOW_PROFILE_ID,
            "success_criteria": ["Answer is grounded in retrieved snippets."],
            "expected_artifacts": ["answer", "retrieval_report"],
        },
        "execution_result": {
            "status": "success",
            "tool_name": "paper_rag_agent",
            "output": "This tool is mainly an observability dashboard SaaS.",
            "artifacts": [
                {"type": "answer", "path": "case_b/failure_answer.md"},
            ],
            "metadata": {"retrieval_strategy": "broad_noisy", "top_k": 12},
        },
        "verification_report": {
            "passed": False,
            "status": "failed",
            "warnings": [
                {
                    "code": "missing_expected_artifact",
                    "message": "retrieval_report missing",
                },
                {
                    "code": "grounding_failed",
                    "message": "answer not grounded in retrieved evidence",
                },
            ],
        },
        "metrics_summary": {"retrieval_hits": 12, "duration_ms": 2300},
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": WORKFLOW_PROFILE_ID,
                "task_type": "rag",
            }
        },
        "realm_evaluation": {
            "status": "fail",
            "recommendation": "observe",
            "requires_human_review": True,
            "reason_codes": ["ungrounded_answer", "artifact_missing"],
            "metadata": {"automatic_action": "none"},
        },
        "baseline_compare_results": {
            "status": "completed",
            "compared_artifact_types": ["answer"],
            "status_counts": {"warning": 1, "breaking": 1},
        },
        "residual_followup": {
            "auto_execution": "none",
            "reassessment": {
                "reassessed_level": "high",
                "needs_followup": True,
                "reason_codes": ["grounding_failed", "retrieval_strategy_regressed"],
            },
            "governance": {"status": "clear", "requires_governance_override": False},
        },
    }


def main() -> None:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    left = write_run_archive(
        archive_root=ARCHIVE_ROOT,
        run_id="case_b_rag_success",
        run_result=build_success_result(),
        created_at=datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC),
        surface_request=build_surface_request("Answer: What is archive-first-harness?"),
        formation_id="paper",
        policy_mode="paper",
    )
    right = write_run_archive(
        archive_root=ARCHIVE_ROOT,
        run_id="case_b_rag_failure",
        run_result=build_failure_result(),
        created_at=datetime(2026, 4, 13, 12, 5, 0, tzinfo=UTC),
        surface_request=build_surface_request("Answer: What is archive-first-harness?"),
        formation_id="paper",
        policy_mode="paper",
    )
    print(
        {
            "status": "ok",
            "archive_root": str(ARCHIVE_ROOT),
            "runs": [left["run_id"], right["run_id"]],
        }
    )


if __name__ == "__main__":
    main()
