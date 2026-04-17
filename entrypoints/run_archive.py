from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from entrypoints._utils import normalize_optional_string, to_json_value


DEFAULT_FORMATION_ID = "default"
DEFAULT_POLICY_MODE = "default"
ARCHIVE_VERSION = "v1"


def write_run_archive(
    *,
    archive_root: str | Path,
    run_id: str,
    run_result: Mapping[str, Any],
    created_at: datetime | None = None,
    surface_request: Mapping[str, Any] | None = None,
    formation_id: str = DEFAULT_FORMATION_ID,
    policy_mode: str = DEFAULT_POLICY_MODE,
    trace_events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(run_result, Mapping):
        raise TypeError("run_result must be a mapping")

    run_id_text = _normalize_required_string(run_id, field_name="run_id")
    archive_root_path = Path(archive_root)
    archive_dir = archive_root_path / run_id_text
    archive_dir.mkdir(parents=True, exist_ok=True)

    timestamp = _coerce_created_at(created_at)
    workflow_profile_id = _extract_workflow_profile_id(run_result)
    manifest = _build_manifest(
        run_id=run_id_text,
        run_result=run_result,
        created_at=timestamp,
        surface_request=surface_request,
        workflow_profile_id=workflow_profile_id,
        formation_id=formation_id,
        policy_mode=policy_mode,
    )
    task_contract = _coerce_mapping(run_result.get("task_contract"))
    profile_and_mode = _build_profile_and_mode(
        run_result=run_result,
        workflow_profile_id=workflow_profile_id,
        formation_id=formation_id,
        policy_mode=policy_mode,
    )
    verification_report = _coerce_mapping(run_result.get("verification_report"))
    metrics_summary = _coerce_mapping(run_result.get("metrics_summary"))
    evaluation_summary = _build_evaluation_summary(run_result)
    final_output = _build_final_output(run_result)
    context_plan = _build_context_plan(
        run_result=run_result,
        workflow_profile_id=workflow_profile_id,
        formation_id=formation_id,
        policy_mode=policy_mode,
    )
    execution_trace = _build_execution_trace(
        trace_events=trace_events,
        run_result=run_result,
        created_at=timestamp,
    )
    failure_signature = _build_failure_signature(run_result)

    written_files = [
        _write_json(archive_dir / "manifest.json", manifest),
        _write_json(archive_dir / "task_contract.json", task_contract),
        _write_json(archive_dir / "profile_and_mode.json", profile_and_mode),
        _write_json(archive_dir / "verification_report.json", verification_report),
        _write_json(archive_dir / "metrics_summary.json", metrics_summary),
        _write_json(archive_dir / "evaluation_summary.json", evaluation_summary),
        _write_json(archive_dir / "final_output.json", final_output),
        _write_json(archive_dir / "context_plan.json", context_plan),
        _write_jsonl(archive_dir / "execution_trace.jsonl", execution_trace),
        _write_json(archive_dir / "failure_signature.json", failure_signature),
    ]

    archive_index = {
        "run_id": run_id_text,
        "archive_dir": str(archive_dir),
        "archive_version": ARCHIVE_VERSION,
        "file_count": len(written_files),
        "files": [Path(item["path"]).name for item in written_files],
        "written_files": written_files,
    }
    archive_index_file = _write_json(archive_dir / "archive_index.json", archive_index)
    written_files.append(archive_index_file)

    index_row = {
        "run_id": run_id_text,
        "created_at": manifest["created_at"],
        "workflow_profile_id": workflow_profile_id,
        "task_type": profile_and_mode["task_type"],
        "formation_id": profile_and_mode["formation_id"],
        "policy_mode": profile_and_mode["policy_mode"],
        "status": manifest["status"],
        "archive_dir": str(archive_dir),
        "failure_class": normalize_optional_string(
            failure_signature.get("failure_class")
        ),
    }
    index_file = append_run_archive_index(archive_root_path / "index.jsonl", index_row)

    return {
        "status": "written",
        "run_id": run_id_text,
        "archive_dir": str(archive_dir),
        "archive_index_file": archive_index_file["path"],
        "index_file": str(index_file),
        "written_files": written_files,
    }


def append_run_archive_index(
    index_file: str | Path,
    entry: Mapping[str, Any],
) -> Path:
    if not isinstance(entry, Mapping):
        raise TypeError("entry must be a mapping")
    index_path = Path(index_file)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(to_json_value(entry), ensure_ascii=True, sort_keys=True) + "\n"
        )
    return index_path


def _build_manifest(
    *,
    run_id: str,
    run_result: Mapping[str, Any],
    created_at: datetime,
    surface_request: Mapping[str, Any] | None,
    workflow_profile_id: str,
    formation_id: str,
    policy_mode: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at": _format_created_at(created_at),
        "workflow_profile_id": workflow_profile_id,
        "formation_id": normalize_optional_string(formation_id) or DEFAULT_FORMATION_ID,
        "policy_mode": normalize_optional_string(policy_mode) or DEFAULT_POLICY_MODE,
        "task_summary": _build_task_summary(surface_request, run_result),
        "status": _build_run_status(run_result),
        "archive_version": ARCHIVE_VERSION,
        "history_entry_written": False,
    }


def _build_profile_and_mode(
    *,
    run_result: Mapping[str, Any],
    workflow_profile_id: str,
    formation_id: str,
    policy_mode: str,
) -> dict[str, Any]:
    surface_payload = _coerce_mapping(run_result.get("surface"))
    task_contract = _coerce_mapping(run_result.get("task_contract"))
    return {
        "workflow_profile_id": workflow_profile_id,
        "task_type": normalize_optional_string(task_contract.get("task_type")) or "",
        "formation_id": normalize_optional_string(formation_id) or DEFAULT_FORMATION_ID,
        "policy_mode": normalize_optional_string(policy_mode) or DEFAULT_POLICY_MODE,
        "profile_resolution": _coerce_mapping(
            surface_payload.get("profile_resolution")
        ),
    }


def _build_evaluation_summary(run_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "evaluation_input_bundle": _coerce_mapping(
            run_result.get("evaluation_input_bundle")
        ),
        "realm_evaluation": _coerce_mapping(run_result.get("realm_evaluation")),
        "baseline_compare_results": _coerce_mapping(
            run_result.get("baseline_compare_results")
        ),
    }


def _build_final_output(run_result: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "execution_result",
        "verification_report",
        "residual_followup",
        "next_actions",
        "working_context_summary",
        "selected_skills",
        "sandbox_triggered",
        "sandbox_decision",
        "sandbox_result",
        "rollback_result",
        "learning_journal",
        "verifier_handoff",
    )
    return {
        key: to_json_value(run_result.get(key)) for key in keys if key in run_result
    }


def _build_context_plan(
    *,
    run_result: Mapping[str, Any],
    workflow_profile_id: str,
    formation_id: str,
    policy_mode: str,
) -> dict[str, Any]:
    block_selection_report = _coerce_mapping(run_result.get("block_selection_report"))
    working_context_summary = _coerce_mapping(run_result.get("working_context_summary"))
    return {
        "workflow_profile_id": workflow_profile_id,
        "formation_id": normalize_optional_string(formation_id) or DEFAULT_FORMATION_ID,
        "policy_mode": normalize_optional_string(policy_mode) or DEFAULT_POLICY_MODE,
        "block_selection_report": block_selection_report,
        "working_context_summary": working_context_summary,
        "context_bias": {
            "included_blocks": list(block_selection_report.get("included_blocks", []))
            if isinstance(block_selection_report.get("included_blocks"), list)
            else [],
            "block_order": list(block_selection_report.get("block_order", []))
            if isinstance(block_selection_report.get("block_order"), list)
            else [],
        },
    }


def _build_execution_trace(
    *,
    trace_events: Sequence[Mapping[str, Any]] | None,
    run_result: Mapping[str, Any],
    created_at: datetime,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if trace_events:
        for item in trace_events:
            if isinstance(item, Mapping):
                events.append(dict(to_json_value(item)))

    if not events:
        events.append(
            _trace_event(
                event_type="runtime_completed",
                status=normalize_optional_string(
                    _mapping_get(run_result, "execution_result.status")
                )
                or "unknown",
                created_at=created_at,
                metadata={
                    "tool_name": _mapping_get(run_result, "execution_result.tool_name"),
                },
            )
        )

    verification_report = _coerce_mapping(run_result.get("verification_report"))
    events.append(
        _trace_event(
            event_type="verification_completed",
            status="passed" if bool(verification_report.get("passed")) else "failed",
            created_at=created_at,
            metadata={
                "warning_count": len(verification_report.get("warnings", []))
                if isinstance(verification_report.get("warnings"), list)
                else 0,
            },
        )
    )
    realm_evaluation = _coerce_mapping(run_result.get("realm_evaluation"))
    events.append(
        _trace_event(
            event_type="evaluation_completed",
            status=normalize_optional_string(realm_evaluation.get("status"))
            or "unknown",
            created_at=created_at,
            metadata={
                "automatic_action": _mapping_get(
                    realm_evaluation, "metadata.automatic_action"
                ),
            },
        )
    )
    return events


def _build_failure_signature(run_result: Mapping[str, Any]) -> dict[str, Any]:
    execution_result = _coerce_mapping(run_result.get("execution_result"))
    verification_report = _coerce_mapping(run_result.get("verification_report"))
    residual_followup = _coerce_mapping(run_result.get("residual_followup"))
    governance = _coerce_mapping(residual_followup.get("governance"))
    execution_status = (
        normalize_optional_string(execution_result.get("status")) or "unknown"
    )

    if execution_status != "success":
        error_payload = _coerce_mapping(execution_result.get("error"))
        failure_class = (
            normalize_optional_string(error_payload.get("type")) or execution_status
        )
        return {
            "status": "failed",
            "failure_class": failure_class,
            "error_type": normalize_optional_string(error_payload.get("type"))
            or failure_class,
            "failed_stage": "execution",
            "message_excerpt": _shorten_text(
                normalize_optional_string(error_payload.get("message")) or ""
            ),
        }
    if verification_report and not bool(verification_report.get("passed")):
        return {
            "status": "failed",
            "failure_class": "verification_failed",
            "error_type": "verification_failed",
            "failed_stage": "verification",
            "message_excerpt": _shorten_text(
                normalize_optional_string(verification_report.get("status")) or ""
            ),
        }
    if bool(governance.get("requires_governance_override")):
        return {
            "status": "failed",
            "failure_class": "governance_review_required",
            "error_type": "governance_review_required",
            "failed_stage": "governance",
            "message_excerpt": _shorten_text(
                normalize_optional_string(governance.get("status")) or ""
            ),
        }
    return {
        "status": "success",
        "failure_class": None,
        "error_type": None,
        "failed_stage": None,
        "message_excerpt": "",
    }


def _build_task_summary(
    surface_request: Mapping[str, Any] | None,
    run_result: Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(surface_request, Mapping):
        task_text = normalize_optional_string(surface_request.get("task")) or ""
    else:
        task_text = ""
    task_contract = _coerce_mapping(run_result.get("task_contract"))
    return {
        "task": task_text or normalize_optional_string(task_contract.get("goal")) or "",
        "task_type": normalize_optional_string(task_contract.get("task_type")) or "",
        "task_id": normalize_optional_string(task_contract.get("task_id")) or "",
        "contract_id": normalize_optional_string(task_contract.get("contract_id"))
        or "",
    }


def _build_run_status(run_result: Mapping[str, Any]) -> str:
    execution_status = (
        normalize_optional_string(_mapping_get(run_result, "execution_result.status"))
        or "unknown"
    )
    verification_passed = bool(_mapping_get(run_result, "verification_report.passed"))
    if execution_status == "success" and verification_passed:
        return "success"
    return "failed"


def _extract_workflow_profile_id(run_result: Mapping[str, Any]) -> str:
    candidates = (
        _mapping_get(run_result, "surface.workflow_profile_id"),
        _mapping_get(run_result, "task_contract.workflow_profile_id"),
        _mapping_get(
            run_result,
            "evaluation_input_bundle.task_contract_summary.workflow_profile_id",
        ),
    )
    for value in candidates:
        text = normalize_optional_string(value)
        if text:
            return text
    return "default_general"


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, str]:
    path.write_text(
        json.dumps(to_json_value(payload), ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {"format": "json", "path": str(path)}


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    serialized_rows = [
        json.dumps(to_json_value(row), ensure_ascii=True, sort_keys=True)
        for row in rows
    ]
    path.write_text(
        "\n".join(serialized_rows) + ("\n" if serialized_rows else ""), encoding="utf-8"
    )
    return {"format": "jsonl", "path": str(path)}


def _trace_event(
    *,
    event_type: str,
    status: str,
    created_at: datetime,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": _format_created_at(created_at),
        "event_type": event_type,
        "status": status,
        "metadata": dict(to_json_value(metadata or {})),
    }


def _coerce_mapping(value: object) -> dict[str, Any]:
    normalized = to_json_value(value)
    if isinstance(normalized, Mapping):
        return dict(normalized)
    return {}


def _mapping_get(mapping: object, path: str) -> object:
    current = mapping
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _shorten_text(value: str, *, limit: int = 160) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _coerce_created_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_created_at(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_required_string(value: object | None, *, field_name: str) -> str:
    text = normalize_optional_string(value)
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    return text
