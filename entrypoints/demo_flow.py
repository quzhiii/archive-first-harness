from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from entrypoints.run_archive import write_run_archive
from entrypoints.settings import Settings


DEMO_WORKFLOW_PROFILE_ID = "demo_quickstart"
DEMO_TASK_TYPE = "demo"
DEMO_SUCCESS_RUN_ID = "demo_success_ping"
DEMO_FAILURE_RUN_ID = "demo_failure_guardrail"
DEMO_SUCCESS_CREATED_AT = datetime(2026, 4, 11, 9, 0, 0, tzinfo=UTC)
DEMO_FAILURE_CREATED_AT = datetime(2026, 4, 11, 9, 5, 0, tzinfo=UTC)


def ensure_demo_archives(
    settings: Settings,
    *,
    archive_root: str | Path | None = None,
) -> dict[str, Any]:
    resolved_archive_root = (
        Path(archive_root)
        if archive_root is not None
        else settings.artifacts_dir / "runs"
    )
    resolved_archive_root.mkdir(parents=True, exist_ok=True)

    success_archive_dir = resolved_archive_root / DEMO_SUCCESS_RUN_ID
    failure_archive_dir = resolved_archive_root / DEMO_FAILURE_RUN_ID

    created: list[str] = []
    existing: list[str] = []

    if success_archive_dir.exists():
        existing.append(DEMO_SUCCESS_RUN_ID)
    else:
        write_run_archive(
            archive_root=resolved_archive_root,
            run_id=DEMO_SUCCESS_RUN_ID,
            run_result=_build_success_demo_result(),
            created_at=DEMO_SUCCESS_CREATED_AT,
            surface_request=_build_surface_request(
                task="DEMO success run for first-run archive browsing",
                task_type=DEMO_TASK_TYPE,
            ),
            formation_id="demo",
            policy_mode="demo",
        )
        created.append(DEMO_SUCCESS_RUN_ID)

    if failure_archive_dir.exists():
        existing.append(DEMO_FAILURE_RUN_ID)
    else:
        write_run_archive(
            archive_root=resolved_archive_root,
            run_id=DEMO_FAILURE_RUN_ID,
            run_result=_build_failure_demo_result(),
            created_at=DEMO_FAILURE_CREATED_AT,
            surface_request=_build_surface_request(
                task="DEMO failure run for first-run archive compare",
                task_type=DEMO_TASK_TYPE,
            ),
            formation_id="demo",
            policy_mode="demo",
        )
        created.append(DEMO_FAILURE_RUN_ID)

    return {
        "status": "ready",
        "archive_root": str(resolved_archive_root),
        "task_type": DEMO_TASK_TYPE,
        "workflow_profile_id": DEMO_WORKFLOW_PROFILE_ID,
        "created_run_ids": created,
        "existing_run_ids": existing,
        "success_run_id": DEMO_SUCCESS_RUN_ID,
        "failure_run_id": DEMO_FAILURE_RUN_ID,
        "browse_hint": f'python -m entrypoints.cli archive --archive-root "{resolved_archive_root}" --task-type {DEMO_TASK_TYPE} --limit 10',
        "success_hint": f'python -m entrypoints.cli archive --archive-root "{resolved_archive_root}" --run-id {DEMO_SUCCESS_RUN_ID}',
        "failure_hint": f'python -m entrypoints.cli archive --archive-root "{resolved_archive_root}" --run-id {DEMO_FAILURE_RUN_ID}',
        "compare_hint": (
            f'python -m entrypoints.cli archive --archive-root "{resolved_archive_root}" '
            f"--compare-run-id {DEMO_SUCCESS_RUN_ID} --compare-run-id {DEMO_FAILURE_RUN_ID}"
        ),
    }


def format_demo_brief(payload: dict[str, Any]) -> str:
    created = ", ".join(payload.get("created_run_ids", [])) or "none"
    existing = ", ".join(payload.get("existing_run_ids", [])) or "none"
    return "\n".join(
        [
            "Demo archives ready",
            f"archive_root: {payload.get('archive_root', '')}",
            f"workflow_profile_id: {payload.get('workflow_profile_id', '')}",
            f"task_type: {payload.get('task_type', '')}",
            f"created_now: {created}",
            f"already_present: {existing}",
            f"success_run_id: {payload.get('success_run_id', '')}",
            f"failure_run_id: {payload.get('failure_run_id', '')}",
            "next:",
            f"- browse: {payload.get('browse_hint', '')}",
            f"- success: {payload.get('success_hint', '')}",
            f"- failure: {payload.get('failure_hint', '')}",
            f"- compare: {payload.get('compare_hint', '')}",
            "note: these are deterministic demo archives, not natural runtime outputs.",
        ]
    )


def _build_surface_request(*, task: str, task_type: str) -> dict[str, Any]:
    return {
        "task": task,
        "task_type": task_type,
        "workflow_profile_id": DEMO_WORKFLOW_PROFILE_ID,
    }


def _build_success_demo_result() -> dict[str, Any]:
    return {
        "surface": {"workflow_profile_id": DEMO_WORKFLOW_PROFILE_ID},
        "task_contract": {
            "goal": "Deterministic demo success run for archive browsing.",
            "task_type": DEMO_TASK_TYPE,
            "task_id": "demo-task-success",
            "contract_id": "demo-contract-success",
            "workflow_profile_id": DEMO_WORKFLOW_PROFILE_ID,
            "success_criteria": ["Show a stable success-like archive."],
            "expected_artifacts": ["demo_report"],
        },
        "execution_result": {
            "status": "success",
            "tool_name": "demo_executor",
            "output": "demo success output",
            "artifacts": [{"type": "demo_report", "path": "demo/success-report.txt"}],
            "metadata": {"demo": True, "scenario": "success_like"},
        },
        "verification_report": {
            "passed": True,
            "status": "passed",
            "warnings": [],
        },
        "metrics_summary": {
            "duration_ms": 12,
            "demo": True,
        },
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": DEMO_WORKFLOW_PROFILE_ID,
                "task_type": DEMO_TASK_TYPE,
            }
        },
        "realm_evaluation": {
            "status": "pass",
            "recommendation": "keep",
            "requires_human_review": False,
            "reason_codes": ["demo_success_baseline"],
            "metadata": {"automatic_action": "none", "demo": True},
        },
        "baseline_compare_results": {
            "status": "completed",
            "artifact_types": ["verification_report"],
            "status_counts": {"compatible": 1},
        },
        "residual_followup": {
            "auto_execution": "none",
            "reassessment": {
                "reassessed_level": "low",
                "needs_followup": False,
                "reason_codes": ["demo_success_clean"],
            },
            "governance": {
                "status": "clear",
                "requires_governance_override": False,
            },
        },
    }


def _build_failure_demo_result() -> dict[str, Any]:
    return {
        "surface": {"workflow_profile_id": DEMO_WORKFLOW_PROFILE_ID},
        "task_contract": {
            "goal": "Deterministic demo failure run for archive compare.",
            "task_type": DEMO_TASK_TYPE,
            "task_id": "demo-task-failure",
            "contract_id": "demo-contract-failure",
            "workflow_profile_id": DEMO_WORKFLOW_PROFILE_ID,
            "success_criteria": ["Show a stable failure-like archive."],
            "expected_artifacts": ["demo_audit_note"],
        },
        "execution_result": {
            "status": "error",
            "tool_name": "demo_executor",
            "output": None,
            "error": {
                "type": "demo_execution_failure",
                "message": "Deterministic demo failure for archive compare.",
            },
            "artifacts": [],
            "metadata": {"demo": True, "scenario": "failure_like"},
        },
        "verification_report": {
            "passed": False,
            "status": "failed",
            "warnings": [
                {
                    "code": "demo_failure",
                    "message": "Deterministic demo verification failure.",
                }
            ],
        },
        "metrics_summary": {
            "duration_ms": 9,
            "demo": True,
        },
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": DEMO_WORKFLOW_PROFILE_ID,
                "task_type": DEMO_TASK_TYPE,
            }
        },
        "realm_evaluation": {
            "status": "fail",
            "recommendation": "observe",
            "requires_human_review": True,
            "reason_codes": ["demo_failure_detected"],
            "metadata": {"automatic_action": "none", "demo": True},
        },
        "baseline_compare_results": {
            "status": "not_requested",
            "artifact_types": [],
            "status_counts": {},
        },
        "residual_followup": {
            "auto_execution": "none",
            "reassessment": {
                "reassessed_level": "high",
                "needs_followup": True,
                "reason_codes": ["demo_execution_failed", "demo_verification_failed"],
            },
            "governance": {
                "status": "clear",
                "requires_governance_override": False,
            },
        },
    }
