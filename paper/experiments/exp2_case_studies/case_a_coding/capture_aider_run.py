from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from entrypoints.run_archive import write_run_archive


ARCHIVE_ROOT = REPO_ROOT / "paper" / "data" / "case_study_archives" / "case_a_coding"
WORKFLOW_PROFILE_ID = "paper_case_a_coding"


def build_surface_request(task: str) -> dict[str, Any]:
    return {
        "task": task,
        "task_type": "coding",
        "workflow_profile_id": WORKFLOW_PROFILE_ID,
    }


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"Missing required field: {key}")
    return value


def _bool(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _list_of_str(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"Field '{key}' must be a list")
    return [str(item).strip() for item in value if str(item).strip()]


def _list_of_dict(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"Field '{key}' must be a list")
    result: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            result.append(item)
    return result


def build_run_result(payload: dict[str, Any]) -> dict[str, Any]:
    task = _required_str(payload, "task")
    run_kind = _required_str(payload, "run_kind")
    execution_status = _required_str(payload, "execution_status")
    verification_passed = _bool(payload, "verification_passed")

    changed_files = _list_of_str(payload, "changed_files")
    expected_artifacts = _list_of_str(payload, "expected_artifacts") or ["file_change"]
    produced_artifacts = _list_of_dict(payload, "produced_artifacts")
    warning_codes = _list_of_str(payload, "warning_codes")
    reassessment_codes = _list_of_str(payload, "reassessment_reason_codes")
    evaluation_codes = _list_of_str(payload, "evaluation_reason_codes")

    output_text = str(payload.get("output_summary") or "").strip() or None
    error_type = str(payload.get("error_type") or "").strip()
    error_message = str(payload.get("error_message") or "").strip()
    tool_name = str(payload.get("tool_name") or "aider").strip() or "aider"
    duration_ms = int(payload.get("duration_ms") or 0)
    files_changed_count = len(changed_files)

    evaluation_status = str(
        payload.get("evaluation_status") or ("pass" if verification_passed else "fail")
    ).strip()
    evaluation_recommendation = str(
        payload.get("evaluation_recommendation")
        or ("keep" if verification_passed else "observe")
    ).strip()
    requires_human_review = _bool(
        payload, "requires_human_review", default=not verification_passed
    )

    reassessed_level = str(
        payload.get("reassessed_level") or ("low" if verification_passed else "high")
    ).strip()
    governance_status = (
        str(payload.get("governance_status") or "clear").strip() or "clear"
    )
    governance_override = _bool(payload, "requires_governance_override")

    warning_messages = {
        "missing_expected_artifact": "Expected code change artifact was not produced.",
        "verification_failed": "Post-change verification did not pass.",
        "wrong_file_changed": "The coding agent changed the wrong file(s).",
        "no_effective_change": "The coding agent produced no effective code change.",
        "manual_review_needed": "Manual review is required before accepting this run.",
    }
    warnings = [
        {"code": code, "message": warning_messages.get(code, code.replace("_", " "))}
        for code in warning_codes
    ]

    if changed_files and not produced_artifacts:
        produced_artifacts = [
            {"type": "file_change", "path": path} for path in changed_files
        ]

    trace_events = payload.get("trace_events")
    if not isinstance(trace_events, list):
        trace_events = [
            {
                "event_type": "coding_agent_run_captured",
                "status": execution_status,
                "metadata": {
                    "tool_name": tool_name,
                    "run_kind": run_kind,
                    "changed_files": changed_files,
                    "verification_passed": verification_passed,
                },
            }
        ]

    return {
        "surface": {"workflow_profile_id": WORKFLOW_PROFILE_ID},
        "task_contract": {
            "goal": task,
            "task_type": "coding",
            "task_id": str(payload.get("task_id") or f"case-a-{run_kind}"),
            "contract_id": str(
                payload.get("contract_id") or f"case-a-{run_kind}-contract"
            ),
            "workflow_profile_id": WORKFLOW_PROFILE_ID,
            "success_criteria": payload.get("success_criteria")
            or ["Apply the intended code change and pass the stated verification."],
            "expected_artifacts": expected_artifacts,
        },
        "execution_result": {
            "status": execution_status,
            "tool_name": tool_name,
            "output": output_text,
            "error": (
                {
                    "type": error_type or "coding_agent_failure",
                    "message": error_message or "Coding agent run failed.",
                }
                if execution_status != "success"
                else None
            ),
            "artifacts": produced_artifacts,
            "metadata": {
                "paper_experiment": "exp2_case_a_coding",
                "run_kind": run_kind,
                "changed_files": changed_files,
                "files_changed_count": files_changed_count,
                "verification_command": str(
                    payload.get("verification_command") or ""
                ).strip(),
                "model": str(payload.get("model") or "").strip(),
                "repo_scope": str(payload.get("repo_scope") or "").strip(),
            },
        },
        "verification_report": {
            "passed": verification_passed,
            "status": "passed" if verification_passed else "failed",
            "warnings": warnings,
        },
        "metrics_summary": {
            "duration_ms": duration_ms,
            "files_changed_count": files_changed_count,
            "verification_command": str(
                payload.get("verification_command") or ""
            ).strip(),
        },
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": WORKFLOW_PROFILE_ID,
                "task_type": "coding",
            }
        },
        "realm_evaluation": {
            "status": evaluation_status,
            "recommendation": evaluation_recommendation,
            "requires_human_review": requires_human_review,
            "reason_codes": evaluation_codes,
            "metadata": {"automatic_action": "none", "paper_experiment": True},
        },
        "baseline_compare_results": {
            "status": str(
                payload.get("baseline_compare_status") or "not_requested"
            ).strip()
            or "not_requested",
            "compared_artifact_types": [
                artifact.get("type", "")
                for artifact in produced_artifacts
                if isinstance(artifact, dict)
            ],
            "status_counts": payload.get("baseline_status_counts")
            if isinstance(payload.get("baseline_status_counts"), dict)
            else {},
        },
        "residual_followup": {
            "auto_execution": "none",
            "reassessment": {
                "reassessed_level": reassessed_level,
                "needs_followup": not verification_passed,
                "reason_codes": reassessment_codes,
            },
            "governance": {
                "status": governance_status,
                "requires_governance_override": governance_override,
            },
        },
        "trace_events": trace_events,
    }


def build_template(run_kind: str) -> dict[str, Any]:
    if run_kind not in {"success", "failure"}:
        raise ValueError("run_kind must be 'success' or 'failure'")

    success = run_kind == "success"
    return {
        "run_kind": run_kind,
        "run_id": f"case_a_coding_{run_kind}",
        "created_at": "2026-04-13T14:00:00+00:00",
        "task": "Use Aider to fix a small, well-scoped bug in the repository.",
        "task_id": f"case-a-{run_kind}",
        "contract_id": f"case-a-{run_kind}-contract",
        "tool_name": "aider",
        "model": "",
        "repo_scope": "",
        "execution_status": "success" if success else "error",
        "output_summary": "Aider modified the target file and reported the change."
        if success
        else "Aider did not complete the intended fix.",
        "error_type": "",
        "error_message": "",
        "verification_passed": success,
        "verification_command": "pytest path/to/test.py",
        "duration_ms": 120000 if success else 180000,
        "changed_files": ["src/example.py"] if success else [],
        "expected_artifacts": ["file_change"],
        "produced_artifacts": [{"type": "file_change", "path": "src/example.py"}]
        if success
        else [],
        "success_criteria": [
            "Apply the intended bug fix.",
            "Pass the stated verification command.",
        ],
        "warning_codes": []
        if success
        else ["verification_failed", "no_effective_change"],
        "evaluation_status": "pass" if success else "fail",
        "evaluation_recommendation": "keep" if success else "observe",
        "requires_human_review": not success,
        "evaluation_reason_codes": ["verified_fix"]
        if success
        else ["verification_failed", "manual_review_needed"],
        "reassessed_level": "low" if success else "high",
        "reassessment_reason_codes": ["verified_fix"]
        if success
        else ["verification_failed", "coding_agent_regressed"],
        "governance_status": "clear",
        "requires_governance_override": False,
        "baseline_compare_status": "not_requested",
        "baseline_status_counts": {},
        "trace_events": [
            {
                "event_type": "coding_agent_run_captured",
                "status": "success" if success else "failed",
                "metadata": {
                    "tool_name": "aider",
                    "run_kind": run_kind,
                    "notes": "Replace this template with real captured details.",
                },
            }
        ],
    }


def write_template(path: Path, run_kind: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_template(run_kind), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture a real coding-agent run into a paper Case A archive."
    )
    parser.add_argument(
        "--input", help="Path to a JSON record describing one real coding-agent run."
    )
    parser.add_argument(
        "--emit-template",
        choices=["success", "failure"],
        help="Write a starter JSON template instead of creating an archive.",
    )
    parser.add_argument(
        "--template-out",
        help="Output path for --emit-template. Defaults to the case folder.",
    )
    parser.add_argument("--run-id", help="Optional override for the archive run_id.")
    args = parser.parse_args()

    if args.emit_template:
        default_name = f"template_{args.emit_template}.json"
        output_path = (
            Path(args.template_out)
            if args.template_out
            else Path(__file__).resolve().parent / default_name
        )
        write_template(output_path, args.emit_template)
        print(
            json.dumps(
                {"status": "template_written", "path": str(output_path)},
                ensure_ascii=False,
            )
        )
        return

    if not args.input:
        raise SystemExit("Either --input or --emit-template is required.")

    input_path = Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Input JSON must be an object.")

    run_result = build_run_result(payload)
    run_id = args.run_id or _required_str(payload, "run_id")
    created_at_raw = str(payload.get("created_at") or "").strip()
    created_at = (
        datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.now(UTC)
    )

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    written = write_run_archive(
        archive_root=ARCHIVE_ROOT,
        run_id=run_id,
        run_result=run_result,
        created_at=created_at,
        surface_request=build_surface_request(_required_str(payload, "task")),
        formation_id="paper",
        policy_mode="paper",
        trace_events=run_result.get("trace_events"),
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "archive_root": str(ARCHIVE_ROOT),
                "run_id": written["run_id"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
