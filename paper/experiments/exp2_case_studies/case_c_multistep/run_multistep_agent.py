from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from entrypoints.run_archive import write_run_archive


ARCHIVE_ROOT = REPO_ROOT / "paper" / "data" / "case_study_archives" / "case_c_multistep"
WORKFLOW_PROFILE_ID = "paper_case_c_multistep"


def build_surface_request(task: str) -> dict:
    return {
        "task": task,
        "task_type": "execution",
        "workflow_profile_id": WORKFLOW_PROFILE_ID,
    }


def build_success_result() -> dict:
    return {
        "surface": {"workflow_profile_id": WORKFLOW_PROFILE_ID},
        "task_contract": {
            "goal": "Collect weather, choose lunch venue, and produce a final note.",
            "task_type": "execution",
            "task_id": "case-c-success",
            "contract_id": "case-c-success-contract",
            "workflow_profile_id": WORKFLOW_PROFILE_ID,
            "success_criteria": [
                "All three steps complete and final note is produced."
            ],
            "expected_artifacts": ["plan_note"],
        },
        "execution_result": {
            "status": "success",
            "tool_name": "paper_multistep_agent",
            "output": "Weather checked, restaurant selected, final note generated.",
            "artifacts": [{"type": "plan_note", "path": "case_c/plan_note.md"}],
            "metadata": {"steps_completed": ["weather", "restaurant", "note"]},
        },
        "verification_report": {"passed": True, "status": "passed", "warnings": []},
        "metrics_summary": {"duration_ms": 1800, "step_count": 3},
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": WORKFLOW_PROFILE_ID,
                "task_type": "execution",
            }
        },
        "realm_evaluation": {
            "status": "pass",
            "recommendation": "keep",
            "requires_human_review": False,
            "reason_codes": ["all_steps_completed"],
            "metadata": {"automatic_action": "none"},
        },
        "baseline_compare_results": {
            "status": "completed",
            "compared_artifact_types": ["plan_note"],
            "status_counts": {"compatible": 1},
        },
        "residual_followup": {
            "auto_execution": "none",
            "reassessment": {
                "reassessed_level": "low",
                "needs_followup": False,
                "reason_codes": ["workflow_complete"],
            },
            "governance": {"status": "clear", "requires_governance_override": False},
        },
    }


def build_failure_result() -> dict:
    return {
        "surface": {"workflow_profile_id": WORKFLOW_PROFILE_ID},
        "task_contract": {
            "goal": "Collect weather, choose lunch venue, and produce a final note.",
            "task_type": "execution",
            "task_id": "case-c-failure",
            "contract_id": "case-c-failure-contract",
            "workflow_profile_id": WORKFLOW_PROFILE_ID,
            "success_criteria": [
                "All three steps complete and final note is produced."
            ],
            "expected_artifacts": ["plan_note"],
        },
        "execution_result": {
            "status": "error",
            "tool_name": "paper_multistep_agent",
            "output": None,
            "error": {
                "type": "restaurant_api_timeout",
                "message": "Step 2 failed while choosing restaurant.",
            },
            "artifacts": [],
            "metadata": {"steps_completed": ["weather"], "failed_step": "restaurant"},
        },
        "verification_report": {
            "passed": False,
            "status": "failed",
            "warnings": [
                {
                    "code": "missing_expected_artifact",
                    "message": "plan_note was not produced",
                }
            ],
        },
        "metrics_summary": {"duration_ms": 30000, "step_count": 2},
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": WORKFLOW_PROFILE_ID,
                "task_type": "execution",
            }
        },
        "realm_evaluation": {
            "status": "fail",
            "recommendation": "observe",
            "requires_human_review": True,
            "reason_codes": ["step2_timeout", "artifact_missing"],
            "metadata": {"automatic_action": "none"},
        },
        "baseline_compare_results": {
            "status": "not_requested",
            "compared_artifact_types": [],
            "status_counts": {},
        },
        "residual_followup": {
            "auto_execution": "none",
            "reassessment": {
                "reassessed_level": "high",
                "needs_followup": True,
                "reason_codes": ["execution_failed", "step2_timeout"],
            },
            "governance": {"status": "clear", "requires_governance_override": False},
        },
    }


def main() -> None:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    left = write_run_archive(
        archive_root=ARCHIVE_ROOT,
        run_id="case_c_multistep_success",
        run_result=build_success_result(),
        created_at=datetime(2026, 4, 13, 13, 0, 0, tzinfo=UTC),
        surface_request=build_surface_request("Plan a lunch outing based on weather."),
        formation_id="paper",
        policy_mode="paper",
    )
    right = write_run_archive(
        archive_root=ARCHIVE_ROOT,
        run_id="case_c_multistep_failure",
        run_result=build_failure_result(),
        created_at=datetime(2026, 4, 13, 13, 5, 0, tzinfo=UTC),
        surface_request=build_surface_request("Plan a lunch outing based on weather."),
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
