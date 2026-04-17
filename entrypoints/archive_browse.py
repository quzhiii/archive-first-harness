from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from entrypoints._utils import (
    extract_mapping,
    normalize_optional_string,
    normalize_string_list,
    normalize_string_list_sorted,
)

RISK_LEVEL_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
}


def browse_run_archives(
    archive_root: str | Path,
    *,
    limit: int = 10,
    workflow_profile_id: str | None = None,
    task_type: str | None = None,
    formation_id: str | None = None,
    status: str | None = None,
    failure_class: str | None = None,
) -> dict[str, Any]:
    if limit < 0:
        raise ValueError("limit must be non-negative")

    archive_root_path = Path(archive_root)
    entries, source = _load_archive_entries(archive_root_path)
    filtered_entries = _filter_archive_entries(
        entries,
        workflow_profile_id=workflow_profile_id,
        task_type=task_type,
        formation_id=formation_id,
        status=status,
        failure_class=failure_class,
    )
    selected_entries = filtered_entries[-limit:] if limit else []
    return {
        "archive_root": str(archive_root_path),
        "index_file": str(archive_root_path / "index.jsonl"),
        "entry_count": len(selected_entries),
        "limit": int(limit),
        "filters": {
            "workflow_profile_id": normalize_optional_string(workflow_profile_id),
            "task_type": normalize_optional_string(task_type),
            "formation_id": normalize_optional_string(formation_id),
            "status": normalize_optional_string(status),
            "failure_class": normalize_optional_string(failure_class),
        },
        "entries": selected_entries,
        "source": source,
    }


def summarize_run_archives(
    archive_root: str | Path,
    *,
    workflow_profile_id: str | None = None,
    task_type: str | None = None,
    formation_id: str | None = None,
    status: str | None = None,
    failure_class: str | None = None,
) -> dict[str, Any]:
    archive_root_path = Path(archive_root)
    entries, source = _load_archive_entries(archive_root_path)
    filtered_entries = _filter_archive_entries(
        entries,
        workflow_profile_id=workflow_profile_id,
        task_type=task_type,
        formation_id=formation_id,
        status=status,
        failure_class=failure_class,
    )
    return {
        "archive_root": str(archive_root_path),
        "index_file": str(archive_root_path / "index.jsonl"),
        "entry_count": len(filtered_entries),
        "filters": {
            "workflow_profile_id": normalize_optional_string(workflow_profile_id),
            "task_type": normalize_optional_string(task_type),
            "formation_id": normalize_optional_string(formation_id),
            "status": normalize_optional_string(status),
            "failure_class": normalize_optional_string(failure_class),
        },
        "oldest": filtered_entries[0] if filtered_entries else None,
        "latest": filtered_entries[-1] if filtered_entries else None,
        "status_counts": _count_archive_field_values(filtered_entries, "status"),
        "task_type_counts": _count_archive_field_values(filtered_entries, "task_type"),
        "formation_counts": _count_archive_field_values(
            filtered_entries, "formation_id"
        ),
        "workflow_profile_counts": _count_archive_field_values(
            filtered_entries, "workflow_profile_id"
        ),
        "failure_class_counts": _count_archive_field_values(
            filtered_entries, "failure_class", default_value="none"
        ),
        "governance_status_counts": _count_archive_field_values(
            filtered_entries, "governance_status", default_value="clear"
        ),
        "missing_expected_warning_counts": {
            "yes": sum(
                1
                for entry in filtered_entries
                if bool(entry.get("missing_expected_artifact_warning"))
            ),
            "no": sum(
                1
                for entry in filtered_entries
                if not bool(entry.get("missing_expected_artifact_warning"))
            ),
        },
        "source": source,
    }


def read_latest_run_archive(
    archive_root: str | Path,
) -> dict[str, Any]:
    archive_root_path = Path(archive_root)
    entries, source = _load_archive_entries(archive_root_path)
    if not entries:
        raise FileNotFoundError(f"no run archives available in {archive_root_path}")
    latest_entry = entries[-1]
    return {
        "archive_root": str(archive_root_path),
        "index_file": str(archive_root_path / "index.jsonl"),
        "latest_archive": latest_entry,
        "archive": _read_archive_record(Path(latest_entry["archive_dir"])),
        "source": source,
    }


def find_run_archive(
    archive_root: str | Path,
    run_id: str,
) -> dict[str, Any]:
    run_id_text = normalize_optional_string(run_id)
    if not run_id_text:
        raise ValueError("run_id must not be empty")

    archive_root_path = Path(archive_root)
    entries, source = _load_archive_entries(archive_root_path)
    entry = _find_archive_entry_by_run_id(entries, run_id_text)
    if entry is None:
        raise LookupError(f"run_id not found: {run_id_text}")
    return {
        "archive_root": str(archive_root_path),
        "index_file": str(archive_root_path / "index.jsonl"),
        "entry": entry,
        "archive": _read_archive_record(Path(entry["archive_dir"])),
        "source": source,
    }


def compare_run_archives(
    archive_root: str | Path,
    left_run_id: str,
    right_run_id: str,
) -> dict[str, Any]:
    left_payload = find_run_archive(archive_root, left_run_id)
    right_payload = find_run_archive(archive_root, right_run_id)

    left_manifest = extract_mapping(left_payload["archive"], "manifest")
    right_manifest = extract_mapping(right_payload["archive"], "manifest")
    left_task_contract = extract_mapping(left_payload["archive"], "task_contract")
    right_task_contract = extract_mapping(right_payload["archive"], "task_contract")
    left_failure = extract_mapping(left_payload["archive"], "failure_signature")
    right_failure = extract_mapping(right_payload["archive"], "failure_signature")
    left_verification = extract_mapping(left_payload["archive"], "verification_report")
    right_verification = extract_mapping(
        right_payload["archive"], "verification_report"
    )
    left_execution_result = extract_mapping(left_payload["archive"], "execution_result")
    right_execution_result = extract_mapping(
        right_payload["archive"], "execution_result"
    )
    left_profile_and_mode = extract_mapping(left_payload["archive"], "profile_and_mode")
    right_profile_and_mode = extract_mapping(
        right_payload["archive"], "profile_and_mode"
    )
    left_residual_followup = extract_mapping(
        left_payload["archive"], "residual_followup"
    )
    right_residual_followup = extract_mapping(
        right_payload["archive"], "residual_followup"
    )
    left_reassessment = extract_mapping(left_residual_followup, "reassessment")
    right_reassessment = extract_mapping(right_residual_followup, "reassessment")
    left_governance = extract_mapping(left_residual_followup, "governance")
    right_governance = extract_mapping(right_residual_followup, "governance")
    left_evaluation_summary = extract_mapping(
        left_payload["archive"], "evaluation_summary"
    )
    right_evaluation_summary = extract_mapping(
        right_payload["archive"], "evaluation_summary"
    )
    left_realm_evaluation = extract_mapping(left_evaluation_summary, "realm_evaluation")
    right_realm_evaluation = extract_mapping(
        right_evaluation_summary, "realm_evaluation"
    )
    left_baseline_compare_results = _extract_optional_mapping(
        left_evaluation_summary, "baseline_compare_results"
    )
    right_baseline_compare_results = _extract_optional_mapping(
        right_evaluation_summary, "baseline_compare_results"
    )
    left_artifact_summary = _build_artifact_summary(
        task_contract=left_task_contract,
        execution_result=left_execution_result,
        verification_report=left_verification,
        baseline_compare_results=left_baseline_compare_results,
    )
    right_artifact_summary = _build_artifact_summary(
        task_contract=right_task_contract,
        execution_result=right_execution_result,
        verification_report=right_verification,
        baseline_compare_results=right_baseline_compare_results,
    )
    left_reassessment_reason_codes = normalize_string_list(
        left_reassessment.get("reason_codes")
    )
    right_reassessment_reason_codes = normalize_string_list(
        right_reassessment.get("reason_codes")
    )
    left_evaluation_reason_codes = normalize_string_list(
        left_realm_evaluation.get("reason_codes")
    )
    right_evaluation_reason_codes = normalize_string_list(
        right_realm_evaluation.get("reason_codes")
    )

    return {
        "archive_root": str(Path(archive_root)),
        "left": {
            "run_id": normalize_optional_string(left_payload["entry"].get("run_id"))
            or "",
            "created_at": normalize_optional_string(
                left_payload["entry"].get("created_at")
            )
            or "",
            "status": normalize_optional_string(left_manifest.get("status")) or "",
            "workflow_profile_id": normalize_optional_string(
                left_manifest.get("workflow_profile_id")
            )
            or "",
            "task_type": normalize_optional_string(
                extract_mapping(left_manifest, "task_summary").get("task_type")
            )
            or normalize_optional_string(left_profile_and_mode.get("task_type"))
            or "",
            "formation_id": normalize_optional_string(
                left_profile_and_mode.get("formation_id")
            )
            or "",
            **left_artifact_summary,
            "failure_class": normalize_optional_string(
                left_failure.get("failure_class")
            )
            or "",
            "failed_stage": normalize_optional_string(left_failure.get("failed_stage"))
            or "",
            "verification_status": normalize_optional_string(
                left_verification.get("status")
            )
            or "",
            "verification_passed": bool(left_verification.get("passed")),
            "reassessed_level": normalize_optional_string(
                left_reassessment.get("reassessed_level")
            )
            or "",
            "followup_needed": bool(left_reassessment.get("needs_followup")),
            "reassessment_reason_codes": left_reassessment_reason_codes,
            "evaluation_status": normalize_optional_string(
                left_realm_evaluation.get("status")
            )
            or "",
            "evaluation_recommendation": normalize_optional_string(
                left_realm_evaluation.get("recommendation")
            )
            or "",
            "evaluation_human_review": bool(
                left_realm_evaluation.get("requires_human_review")
            ),
            "evaluation_reason_codes": left_evaluation_reason_codes,
            "governance_status": normalize_optional_string(
                left_governance.get("status")
            )
            or "",
            "governance_required": bool(
                left_governance.get("requires_governance_override")
            ),
            "task": normalize_optional_string(
                extract_mapping(left_manifest, "task_summary").get("task")
            )
            or "",
        },
        "right": {
            "run_id": normalize_optional_string(right_payload["entry"].get("run_id"))
            or "",
            "created_at": normalize_optional_string(
                right_payload["entry"].get("created_at")
            )
            or "",
            "status": normalize_optional_string(right_manifest.get("status")) or "",
            "workflow_profile_id": normalize_optional_string(
                right_manifest.get("workflow_profile_id")
            )
            or "",
            "task_type": normalize_optional_string(
                extract_mapping(right_manifest, "task_summary").get("task_type")
            )
            or normalize_optional_string(right_profile_and_mode.get("task_type"))
            or "",
            "formation_id": normalize_optional_string(
                right_profile_and_mode.get("formation_id")
            )
            or "",
            **right_artifact_summary,
            "failure_class": normalize_optional_string(
                right_failure.get("failure_class")
            )
            or "",
            "failed_stage": normalize_optional_string(right_failure.get("failed_stage"))
            or "",
            "verification_status": normalize_optional_string(
                right_verification.get("status")
            )
            or "",
            "verification_passed": bool(right_verification.get("passed")),
            "reassessed_level": normalize_optional_string(
                right_reassessment.get("reassessed_level")
            )
            or "",
            "followup_needed": bool(right_reassessment.get("needs_followup")),
            "reassessment_reason_codes": right_reassessment_reason_codes,
            "evaluation_status": normalize_optional_string(
                right_realm_evaluation.get("status")
            )
            or "",
            "evaluation_recommendation": normalize_optional_string(
                right_realm_evaluation.get("recommendation")
            )
            or "",
            "evaluation_human_review": bool(
                right_realm_evaluation.get("requires_human_review")
            ),
            "evaluation_reason_codes": right_evaluation_reason_codes,
            "governance_status": normalize_optional_string(
                right_governance.get("status")
            )
            or "",
            "governance_required": bool(
                right_governance.get("requires_governance_override")
            ),
            "task": normalize_optional_string(
                extract_mapping(right_manifest, "task_summary").get("task")
            )
            or "",
        },
        "comparison": {
            "same_status": left_manifest.get("status") == right_manifest.get("status"),
            "same_workflow_profile_id": left_manifest.get("workflow_profile_id")
            == right_manifest.get("workflow_profile_id"),
            "same_task_type": extract_mapping(left_manifest, "task_summary").get(
                "task_type"
            )
            == extract_mapping(right_manifest, "task_summary").get("task_type"),
            "same_formation_id": left_profile_and_mode.get("formation_id")
            == right_profile_and_mode.get("formation_id"),
            "same_expected_artifacts": left_artifact_summary["expected_artifacts"]
            == right_artifact_summary["expected_artifacts"],
            "expected_artifacts_added": _list_added_items(
                left_artifact_summary["expected_artifacts"],
                right_artifact_summary["expected_artifacts"],
            ),
            "expected_artifacts_removed": _list_removed_items(
                left_artifact_summary["expected_artifacts"],
                right_artifact_summary["expected_artifacts"],
            ),
            "same_produced_artifact_types": left_artifact_summary[
                "produced_artifact_types"
            ]
            == right_artifact_summary["produced_artifact_types"],
            "produced_artifact_types_added": _list_added_items(
                left_artifact_summary["produced_artifact_types"],
                right_artifact_summary["produced_artifact_types"],
            ),
            "produced_artifact_types_removed": _list_removed_items(
                left_artifact_summary["produced_artifact_types"],
                right_artifact_summary["produced_artifact_types"],
            ),
            "same_produced_artifact_count": left_artifact_summary[
                "produced_artifact_count"
            ]
            == right_artifact_summary["produced_artifact_count"],
            "same_baseline_compare_status": left_artifact_summary[
                "baseline_compare_status"
            ]
            == right_artifact_summary["baseline_compare_status"],
            "same_baseline_compared_artifact_types": left_artifact_summary[
                "baseline_compared_artifact_types"
            ]
            == right_artifact_summary["baseline_compared_artifact_types"],
            "baseline_compared_artifact_types_added": _list_added_items(
                left_artifact_summary["baseline_compared_artifact_types"],
                right_artifact_summary["baseline_compared_artifact_types"],
            ),
            "baseline_compared_artifact_types_removed": _list_removed_items(
                left_artifact_summary["baseline_compared_artifact_types"],
                right_artifact_summary["baseline_compared_artifact_types"],
            ),
            "same_baseline_status_counts": left_artifact_summary[
                "baseline_status_counts"
            ]
            == right_artifact_summary["baseline_status_counts"],
            "same_missing_expected_artifact_warning": left_artifact_summary[
                "missing_expected_artifact_warning"
            ]
            == right_artifact_summary["missing_expected_artifact_warning"],
            "same_failure_class": left_failure.get("failure_class")
            == right_failure.get("failure_class"),
            "same_failed_stage": left_failure.get("failed_stage")
            == right_failure.get("failed_stage"),
            "same_verification_status": left_verification.get("status")
            == right_verification.get("status"),
            "same_reassessed_level": left_reassessment.get("reassessed_level")
            == right_reassessment.get("reassessed_level"),
            "same_followup_needed": bool(left_reassessment.get("needs_followup"))
            == bool(right_reassessment.get("needs_followup")),
            "same_reassessment_reason_codes": left_reassessment_reason_codes
            == right_reassessment_reason_codes,
            "reassessment_reason_codes_added": _list_added_items(
                left_reassessment_reason_codes, right_reassessment_reason_codes
            ),
            "reassessment_reason_codes_removed": _list_removed_items(
                left_reassessment_reason_codes, right_reassessment_reason_codes
            ),
            "same_evaluation_status": left_realm_evaluation.get("status")
            == right_realm_evaluation.get("status"),
            "same_evaluation_recommendation": left_realm_evaluation.get(
                "recommendation"
            )
            == right_realm_evaluation.get("recommendation"),
            "same_evaluation_human_review": bool(
                left_realm_evaluation.get("requires_human_review")
            )
            == bool(right_realm_evaluation.get("requires_human_review")),
            "same_evaluation_reason_codes": left_evaluation_reason_codes
            == right_evaluation_reason_codes,
            "evaluation_reason_codes_added": _list_added_items(
                left_evaluation_reason_codes, right_evaluation_reason_codes
            ),
            "evaluation_reason_codes_removed": _list_removed_items(
                left_evaluation_reason_codes, right_evaluation_reason_codes
            ),
            "same_governance_status": left_governance.get("status")
            == right_governance.get("status"),
            "same_governance_required": bool(
                left_governance.get("requires_governance_override")
            )
            == bool(right_governance.get("requires_governance_override")),
            "same_task": extract_mapping(left_manifest, "task_summary").get("task")
            == extract_mapping(right_manifest, "task_summary").get("task"),
            "failure_transition": _classify_failure_transition(
                left_manifest, right_manifest, left_failure, right_failure
            ),
            "verification_transition": _classify_quality_boolean_transition(
                bool(left_verification.get("passed")),
                bool(right_verification.get("passed")),
                truthy_is_good=True,
                improved_label="improved",
                regressed_label="regressed",
            ),
            "reassessment_transition": _classify_risk_transition(
                normalize_optional_string(left_reassessment.get("reassessed_level")),
                normalize_optional_string(right_reassessment.get("reassessed_level")),
            ),
            "evaluation_transition": _classify_evaluation_transition(
                left_realm_evaluation, right_realm_evaluation
            ),
            "governance_transition": _classify_quality_boolean_transition(
                bool(left_governance.get("requires_governance_override")),
                bool(right_governance.get("requires_governance_override")),
                truthy_is_good=False,
                improved_label="cleared",
                regressed_label="escalated",
            ),
            "artifact_transition": _classify_artifact_transition(
                left_artifact_summary, right_artifact_summary
            ),
        },
    }


def format_archive_brief(payload: Mapping[str, Any]) -> str:
    if "comparison" in payload:
        return _format_archive_comparison(payload)
    if "status_counts" in payload and "task_type_counts" in payload:
        return _format_archive_trend_summary(payload)
    if "latest_archive" in payload and "archive" in payload:
        return _format_latest_archive_payload(payload)
    if "entry" in payload and "archive" in payload:
        return _format_archive_entry_payload(payload)
    if isinstance(payload.get("entries"), list):
        return _format_archive_summary_payload(payload)
    raise ValueError("archive payload is invalid")


def _read_archive_record(archive_dir: Path) -> dict[str, Any]:
    if not archive_dir.exists():
        raise FileNotFoundError(f"archive directory does not exist: {archive_dir}")
    final_output = _read_json_mapping(archive_dir / "final_output.json")
    return {
        "manifest": _read_json_mapping(archive_dir / "manifest.json"),
        "task_contract": _read_json_mapping(archive_dir / "task_contract.json"),
        "failure_signature": _read_json_mapping(archive_dir / "failure_signature.json"),
        "profile_and_mode": _read_json_mapping(archive_dir / "profile_and_mode.json"),
        "verification_report": _read_json_mapping(
            archive_dir / "verification_report.json"
        ),
        "execution_result": _extract_optional_mapping(final_output, "execution_result"),
        "residual_followup": _extract_optional_mapping(
            final_output,
            "residual_followup",
        ),
        "evaluation_summary": _read_json_mapping(
            archive_dir / "evaluation_summary.json"
        ),
        "archive_index": _read_json_mapping(archive_dir / "archive_index.json"),
    }


def _load_archive_entries(archive_root: Path) -> tuple[list[dict[str, Any]], str]:
    index_file = archive_root / "index.jsonl"
    if index_file.exists():
        index_entries, bad_line_count = _read_archive_index_entries(index_file)
        scanned_entries = _scan_archive_dirs(archive_root)
        merged_entries = _merge_archive_entries(index_entries, scanned_entries)
        if bad_line_count or len(merged_entries) != len(index_entries):
            return merged_entries, "index_file+archive_dirs"
        return merged_entries, "index_file"
    return _scan_archive_dirs(archive_root), "archive_dirs"


def _read_archive_index_entries(index_file: Path) -> tuple[list[dict[str, Any]], int]:
    if not index_file.exists():
        raise FileNotFoundError(f"no run archives available in {index_file.parent}")
    entries: list[dict[str, Any]] = []
    bad_line_count = 0
    for line in index_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            bad_line_count += 1
            continue
        if isinstance(payload, Mapping):
            entries.append(_hydrate_archive_index_entry(dict(payload)))
    return entries, bad_line_count


def _merge_archive_entries(
    index_entries: list[dict[str, Any]],
    scanned_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_run_id: dict[str, dict[str, Any]] = {}
    anonymous_entries: list[dict[str, Any]] = []

    for entry in index_entries:
        run_id = normalize_optional_string(entry.get("run_id"))
        if run_id:
            merged_by_run_id[run_id] = entry
        else:
            anonymous_entries.append(entry)

    for entry in scanned_entries:
        run_id = normalize_optional_string(entry.get("run_id"))
        if not run_id:
            anonymous_entries.append(entry)
            continue
        if run_id not in merged_by_run_id:
            merged_by_run_id[run_id] = entry

    merged_entries = list(merged_by_run_id.values()) + anonymous_entries
    merged_entries.sort(
        key=lambda item: normalize_optional_string(item.get("created_at")) or ""
    )
    return merged_entries


def _hydrate_archive_index_entry(entry: dict[str, Any]) -> dict[str, Any]:
    archive_dir_text = normalize_optional_string(entry.get("archive_dir"))
    if not archive_dir_text:
        return entry

    archive_dir = Path(archive_dir_text)
    manifest = (
        _read_json_mapping(archive_dir / "manifest.json")
        if (archive_dir / "manifest.json").exists()
        else {}
    )
    profile_and_mode = (
        _read_json_mapping(archive_dir / "profile_and_mode.json")
        if (archive_dir / "profile_and_mode.json").exists()
        else {}
    )
    failure_signature = (
        _read_json_mapping(archive_dir / "failure_signature.json")
        if (archive_dir / "failure_signature.json").exists()
        else {}
    )
    verification_report = (
        _read_json_mapping(archive_dir / "verification_report.json")
        if (archive_dir / "verification_report.json").exists()
        else {}
    )
    final_output = (
        _read_json_mapping(archive_dir / "final_output.json")
        if (archive_dir / "final_output.json").exists()
        else {}
    )
    task_summary = _extract_optional_mapping(manifest, "task_summary")
    governance = _extract_optional_mapping(
        _extract_optional_mapping(final_output, "residual_followup"), "governance"
    )
    warning_codes = _verification_warning_codes(verification_report)

    hydrated = dict(entry)
    if "task_type" not in hydrated:
        hydrated["task_type"] = (
            normalize_optional_string(task_summary.get("task_type"))
            or normalize_optional_string(profile_and_mode.get("task_type"))
            or ""
        )
    if "formation_id" not in hydrated:
        hydrated["formation_id"] = (
            normalize_optional_string(profile_and_mode.get("formation_id")) or ""
        )
    if "policy_mode" not in hydrated:
        hydrated["policy_mode"] = (
            normalize_optional_string(profile_and_mode.get("policy_mode")) or ""
        )
    if "workflow_profile_id" not in hydrated:
        hydrated["workflow_profile_id"] = (
            normalize_optional_string(manifest.get("workflow_profile_id")) or ""
        )
    if "status" not in hydrated:
        hydrated["status"] = normalize_optional_string(manifest.get("status")) or ""
    if "failure_class" not in hydrated:
        hydrated["failure_class"] = normalize_optional_string(
            failure_signature.get("failure_class")
        )
    if "governance_status" not in hydrated:
        hydrated["governance_status"] = (
            normalize_optional_string(governance.get("status")) or ""
        )
    if "governance_required" not in hydrated:
        hydrated["governance_required"] = bool(
            governance.get("requires_governance_override")
        )
    if "missing_expected_artifact_warning" not in hydrated:
        hydrated["missing_expected_artifact_warning"] = (
            "missing_expected_artifact" in warning_codes
        )
    return hydrated


def _scan_archive_dirs(archive_root: Path) -> list[dict[str, Any]]:
    if not archive_root.exists():
        raise FileNotFoundError(f"no run archives available in {archive_root}")

    entries: list[dict[str, Any]] = []
    for path in archive_root.iterdir():
        if not path.is_dir():
            continue
        manifest_path = path / "manifest.json"
        failure_path = path / "failure_signature.json"
        if not manifest_path.exists() or not failure_path.exists():
            continue
        manifest = _read_json_mapping(manifest_path)
        failure_signature = _read_json_mapping(failure_path)
        profile_path = path / "profile_and_mode.json"
        profile_and_mode = (
            _read_json_mapping(profile_path) if profile_path.exists() else {}
        )
        verification_report = (
            _read_json_mapping(path / "verification_report.json")
            if (path / "verification_report.json").exists()
            else {}
        )
        final_output = (
            _read_json_mapping(path / "final_output.json")
            if (path / "final_output.json").exists()
            else {}
        )
        governance = _extract_optional_mapping(
            _extract_optional_mapping(final_output, "residual_followup"), "governance"
        )
        entries.append(
            {
                "run_id": normalize_optional_string(manifest.get("run_id"))
                or path.name,
                "created_at": normalize_optional_string(manifest.get("created_at"))
                or "",
                "workflow_profile_id": normalize_optional_string(
                    manifest.get("workflow_profile_id")
                )
                or "",
                "task_type": normalize_optional_string(
                    extract_mapping(manifest, "task_summary").get("task_type")
                )
                or normalize_optional_string(profile_and_mode.get("task_type"))
                or "",
                "formation_id": normalize_optional_string(
                    profile_and_mode.get("formation_id")
                )
                or "",
                "policy_mode": normalize_optional_string(
                    profile_and_mode.get("policy_mode")
                )
                or "",
                "status": normalize_optional_string(manifest.get("status")) or "",
                "archive_dir": str(path),
                "failure_class": normalize_optional_string(
                    failure_signature.get("failure_class")
                ),
                "governance_status": normalize_optional_string(governance.get("status"))
                or "",
                "governance_required": bool(
                    governance.get("requires_governance_override")
                ),
                "missing_expected_artifact_warning": "missing_expected_artifact"
                in _verification_warning_codes(verification_report),
            }
        )

    if not entries:
        raise FileNotFoundError(f"no run archives available in {archive_root}")
    entries.sort(
        key=lambda item: (
            normalize_optional_string(item.get("created_at")) or "",
            normalize_optional_string(item.get("run_id")) or "",
        )
    )
    return entries


def _filter_archive_entries(
    entries: list[dict[str, Any]],
    *,
    workflow_profile_id: str | None,
    task_type: str | None,
    formation_id: str | None,
    status: str | None,
    failure_class: str | None,
) -> list[dict[str, Any]]:
    workflow_profile_id_text = normalize_optional_string(workflow_profile_id)
    task_type_text = normalize_optional_string(task_type)
    formation_id_text = normalize_optional_string(formation_id)
    status_text = normalize_optional_string(status)
    failure_class_text = normalize_optional_string(failure_class)

    filtered: list[dict[str, Any]] = []
    for entry in entries:
        if (
            workflow_profile_id_text
            and normalize_optional_string(entry.get("workflow_profile_id"))
            != workflow_profile_id_text
        ):
            continue
        if (
            task_type_text
            and normalize_optional_string(entry.get("task_type")) != task_type_text
        ):
            continue
        if (
            formation_id_text
            and normalize_optional_string(entry.get("formation_id"))
            != formation_id_text
        ):
            continue
        if (
            status_text
            and normalize_optional_string(entry.get("status")) != status_text
        ):
            continue
        if (
            failure_class_text
            and normalize_optional_string(entry.get("failure_class"))
            != failure_class_text
        ):
            continue
        filtered.append(entry)
    return filtered


def _find_archive_entry_by_run_id(
    entries: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any] | None:
    for entry in entries:
        if normalize_optional_string(entry.get("run_id")) == run_id:
            return entry
    return None


def _format_latest_archive_payload(payload: Mapping[str, Any]) -> str:
    archive_payload = {
        "archive_root": payload.get("archive_root"),
        "source": payload.get("source"),
        "entry": extract_mapping(payload, "latest_archive"),
        "archive": extract_mapping(payload, "archive"),
    }
    lines = _format_archive_entry_payload(archive_payload).splitlines()
    if lines:
        lines[0] = "Latest archive"
    return "\n".join(lines)


def _format_archive_entry_payload(payload: Mapping[str, Any]) -> str:
    entry = extract_mapping(payload, "entry")
    archive = extract_mapping(payload, "archive")
    manifest = extract_mapping(archive, "manifest")
    task_contract = extract_mapping(archive, "task_contract")
    failure_signature = extract_mapping(archive, "failure_signature")
    profile_and_mode = extract_mapping(archive, "profile_and_mode")
    verification_report = extract_mapping(archive, "verification_report")
    execution_result = extract_mapping(archive, "execution_result")
    governance = extract_mapping(
        extract_mapping(archive, "residual_followup"), "governance"
    )
    baseline_compare_results = _extract_optional_mapping(
        extract_mapping(archive, "evaluation_summary"), "baseline_compare_results"
    )
    task_summary = extract_mapping(manifest, "task_summary")
    artifact_summary = _build_artifact_summary(
        task_contract=task_contract,
        execution_result=execution_result,
        verification_report=verification_report,
        baseline_compare_results=baseline_compare_results,
    )
    return "\n".join(
        [
            "Archive entry",
            f"source: {normalize_optional_string(payload.get('source')) or 'unknown'}",
            f"archive_root: {normalize_optional_string(payload.get('archive_root')) or ''}",
            f"run_id: {normalize_optional_string(entry.get('run_id')) or ''}",
            f"created_at: {normalize_optional_string(entry.get('created_at')) or ''}",
            f"workflow_profile_id: {normalize_optional_string(manifest.get('workflow_profile_id')) or ''}",
            f"task_type: {normalize_optional_string(task_summary.get('task_type')) or ''}",
            f"status: {normalize_optional_string(manifest.get('status')) or ''}",
            f"failure_class: {normalize_optional_string(failure_signature.get('failure_class')) or 'none'}",
            f"failed_stage: {normalize_optional_string(failure_signature.get('failed_stage')) or 'none'}",
            f"verification_status: {normalize_optional_string(verification_report.get('status')) or ''}",
            f"governance_status: {normalize_optional_string(governance.get('status')) or ''}",
            f"governance_required: {'yes' if bool(governance.get('requires_governance_override')) else 'no'}",
            f"formation_id: {normalize_optional_string(profile_and_mode.get('formation_id')) or ''}",
            f"policy_mode: {normalize_optional_string(profile_and_mode.get('policy_mode')) or ''}",
            f"expected_artifacts: {_format_text_list(artifact_summary.get('expected_artifacts'))}",
            f"produced_artifacts: {_format_text_list(artifact_summary.get('produced_artifact_types'))}",
            f"produced_artifact_count: {int(artifact_summary.get('produced_artifact_count', 0) or 0)}",
            f"baseline_compare_status: {normalize_optional_string(artifact_summary.get('baseline_compare_status')) or 'none'}",
            f"baseline_artifacts: {_format_text_list(artifact_summary.get('baseline_compared_artifact_types'))}",
            f"baseline_status_counts: {_format_status_counts(artifact_summary.get('baseline_status_counts'))}",
            f"missing_expected_artifact_warning: {'yes' if bool(artifact_summary.get('missing_expected_artifact_warning')) else 'no'}",
            f"task: {normalize_optional_string(task_summary.get('task')) or ''}",
            f"archive_dir: {normalize_optional_string(entry.get('archive_dir')) or ''}",
        ]
    )


def _format_archive_summary_payload(payload: Mapping[str, Any]) -> str:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("archive summary payload is invalid")
    filters = extract_mapping(payload, "filters")
    lines = [
        "Archive summary",
        f"source: {normalize_optional_string(payload.get('source')) or 'unknown'}",
        f"archive_root: {normalize_optional_string(payload.get('archive_root')) or ''}",
        f"entry_count: {int(payload.get('entry_count', 0) or 0)}",
        f"limit: {int(payload.get('limit', 0) or 0)}",
        "filters: "
        + f"workflow_profile_id={normalize_optional_string(filters.get('workflow_profile_id')) or 'any'} "
        + f"task_type={normalize_optional_string(filters.get('task_type')) or 'any'} "
        + f"formation_id={normalize_optional_string(filters.get('formation_id')) or 'any'} "
        + f"status={normalize_optional_string(filters.get('status')) or 'any'} "
        + f"failure_class={normalize_optional_string(filters.get('failure_class')) or 'any'}",
    ]
    if not entries:
        lines.append("entries: none")
        return "\n".join(lines)
    lines.append("entries:")
    for entry in entries:
        lines.append(
            "- "
            + f"{normalize_optional_string(entry.get('run_id')) or ''} | "
            + f"{normalize_optional_string(entry.get('created_at')) or ''} | "
            + f"profile={normalize_optional_string(entry.get('workflow_profile_id')) or ''} | "
            + f"task_type={normalize_optional_string(entry.get('task_type')) or ''} | "
            + f"formation={normalize_optional_string(entry.get('formation_id')) or ''} | "
            + f"status={normalize_optional_string(entry.get('status')) or ''} | "
            + f"failure={normalize_optional_string(entry.get('failure_class')) or 'none'} | "
            + f"governance={normalize_optional_string(entry.get('governance_status')) or 'clear'} | "
            + f"gov_required={'yes' if bool(entry.get('governance_required')) else 'no'} | "
            + f"missing_expected={'yes' if bool(entry.get('missing_expected_artifact_warning')) else 'no'} | "
            + f"archive_dir={normalize_optional_string(entry.get('archive_dir')) or ''}"
        )
    return "\n".join(lines)


def _format_archive_trend_summary(payload: Mapping[str, Any]) -> str:
    filters = extract_mapping(payload, "filters")
    oldest = _extract_optional_mapping(payload, "oldest")
    latest = _extract_optional_mapping(payload, "latest")
    lines = [
        "Archive trend summary",
        f"source: {normalize_optional_string(payload.get('source')) or 'unknown'}",
        f"archive_root: {normalize_optional_string(payload.get('archive_root')) or ''}",
        f"entry_count: {int(payload.get('entry_count', 0) or 0)}",
        "filters: "
        + f"workflow_profile_id={normalize_optional_string(filters.get('workflow_profile_id')) or 'any'} "
        + f"task_type={normalize_optional_string(filters.get('task_type')) or 'any'} "
        + f"formation_id={normalize_optional_string(filters.get('formation_id')) or 'any'} "
        + f"status={normalize_optional_string(filters.get('status')) or 'any'} "
        + f"failure_class={normalize_optional_string(filters.get('failure_class')) or 'any'}",
    ]
    if not int(payload.get("entry_count", 0) or 0):
        lines.append("range: none")
        lines.append("status_counts: none")
        lines.append("task_type_counts: none")
        lines.append("formation_counts: none")
        lines.append("workflow_profile_counts: none")
        lines.append("failure_class_counts: none")
        lines.append("governance_status_counts: none")
        lines.append("missing_expected_warning_counts: yes:0,no:0")
        return "\n".join(lines)
    lines.extend(
        [
            "range: "
            + f"oldest={normalize_optional_string(oldest.get('run_id')) or ''}@{normalize_optional_string(oldest.get('created_at')) or ''} "
            + f"latest={normalize_optional_string(latest.get('run_id')) or ''}@{normalize_optional_string(latest.get('created_at')) or ''}",
            f"status_counts: {_format_status_counts(payload.get('status_counts'))}",
            f"task_type_counts: {_format_status_counts(payload.get('task_type_counts'))}",
            f"formation_counts: {_format_status_counts(payload.get('formation_counts'))}",
            f"workflow_profile_counts: {_format_status_counts(payload.get('workflow_profile_counts'))}",
            f"failure_class_counts: {_format_status_counts(payload.get('failure_class_counts'))}",
            f"governance_status_counts: {_format_status_counts(payload.get('governance_status_counts'))}",
            f"missing_expected_warning_counts: {_format_status_counts(payload.get('missing_expected_warning_counts'))}",
        ]
    )
    return "\n".join(lines)


def _count_archive_field_values(
    entries: list[dict[str, Any]],
    field_name: str,
    *,
    default_value: str = "unknown",
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        value = normalize_optional_string(entry.get(field_name)) or default_value
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _format_archive_comparison(payload: Mapping[str, Any]) -> str:
    left = extract_mapping(payload, "left")
    right = extract_mapping(payload, "right")
    comparison = extract_mapping(payload, "comparison")
    return "\n".join(
        [
            "Archive comparison",
            f"archive_root: {normalize_optional_string(payload.get('archive_root')) or ''}",
            "left: "
            + f"{normalize_optional_string(left.get('run_id')) or ''} | "
            + f"status={normalize_optional_string(left.get('status')) or ''} | "
            + f"profile={normalize_optional_string(left.get('workflow_profile_id')) or ''} | "
            + f"task_type={normalize_optional_string(left.get('task_type')) or ''} | "
            + f"formation={normalize_optional_string(left.get('formation_id')) or ''} | "
            + f"failure={normalize_optional_string(left.get('failure_class')) or 'none'} | "
            + f"stage={normalize_optional_string(left.get('failed_stage')) or 'none'} | "
            + f"verification={normalize_optional_string(left.get('verification_status')) or ''} | "
            + f"risk={normalize_optional_string(left.get('reassessed_level')) or ''} | "
            + f"followup={'yes' if bool(left.get('followup_needed')) else 'no'} | "
            + f"reassessment_reasons={_format_reason_codes(left.get('reassessment_reason_codes'))} | "
            + f"evaluation={normalize_optional_string(left.get('evaluation_recommendation')) or ''} | "
            + f"human_review={'yes' if bool(left.get('evaluation_human_review')) else 'no'} | "
            + f"evaluation_reasons={_format_reason_codes(left.get('evaluation_reason_codes'))} | "
            + f"governance={normalize_optional_string(left.get('governance_status')) or ''} | "
            + f"gov_required={'yes' if bool(left.get('governance_required')) else 'no'}",
            "right: "
            + f"{normalize_optional_string(right.get('run_id')) or ''} | "
            + f"status={normalize_optional_string(right.get('status')) or ''} | "
            + f"profile={normalize_optional_string(right.get('workflow_profile_id')) or ''} | "
            + f"task_type={normalize_optional_string(right.get('task_type')) or ''} | "
            + f"formation={normalize_optional_string(right.get('formation_id')) or ''} | "
            + f"failure={normalize_optional_string(right.get('failure_class')) or 'none'} | "
            + f"stage={normalize_optional_string(right.get('failed_stage')) or 'none'} | "
            + f"verification={normalize_optional_string(right.get('verification_status')) or ''} | "
            + f"risk={normalize_optional_string(right.get('reassessed_level')) or ''} | "
            + f"followup={'yes' if bool(right.get('followup_needed')) else 'no'} | "
            + f"reassessment_reasons={_format_reason_codes(right.get('reassessment_reason_codes'))} | "
            + f"evaluation={normalize_optional_string(right.get('evaluation_recommendation')) or ''} | "
            + f"human_review={'yes' if bool(right.get('evaluation_human_review')) else 'no'} | "
            + f"evaluation_reasons={_format_reason_codes(right.get('evaluation_reason_codes'))} | "
            + f"governance={normalize_optional_string(right.get('governance_status')) or ''} | "
            + f"gov_required={'yes' if bool(right.get('governance_required')) else 'no'}",
            "comparison: "
            + f"same_status={'yes' if bool(comparison.get('same_status')) else 'no'} "
            + f"same_profile={'yes' if bool(comparison.get('same_workflow_profile_id')) else 'no'} "
            + f"same_task_type={'yes' if bool(comparison.get('same_task_type')) else 'no'} "
            + f"same_formation={'yes' if bool(comparison.get('same_formation_id')) else 'no'} "
            + f"same_failure={'yes' if bool(comparison.get('same_failure_class')) else 'no'} "
            + f"same_stage={'yes' if bool(comparison.get('same_failed_stage')) else 'no'} "
            + f"same_verification={'yes' if bool(comparison.get('same_verification_status')) else 'no'} "
            + f"same_risk={'yes' if bool(comparison.get('same_reassessed_level')) else 'no'} "
            + f"same_followup={'yes' if bool(comparison.get('same_followup_needed')) else 'no'} "
            + f"same_reassessment_reasons={'yes' if bool(comparison.get('same_reassessment_reason_codes')) else 'no'} "
            + f"same_evaluation={'yes' if bool(comparison.get('same_evaluation_recommendation')) else 'no'} "
            + f"same_human_review={'yes' if bool(comparison.get('same_evaluation_human_review')) else 'no'} "
            + f"same_evaluation_reasons={'yes' if bool(comparison.get('same_evaluation_reason_codes')) else 'no'} "
            + f"same_expected_artifacts={'yes' if bool(comparison.get('same_expected_artifacts')) else 'no'} "
            + f"same_produced_artifacts={'yes' if bool(comparison.get('same_produced_artifact_types')) else 'no'} "
            + f"same_baseline_artifacts={'yes' if bool(comparison.get('same_baseline_compared_artifact_types')) else 'no'} "
            + f"same_baseline_status_counts={'yes' if bool(comparison.get('same_baseline_status_counts')) else 'no'} "
            + f"same_missing_expected={'yes' if bool(comparison.get('same_missing_expected_artifact_warning')) else 'no'} "
            + f"same_governance={'yes' if bool(comparison.get('same_governance_status')) else 'no'} "
            + f"same_governance_required={'yes' if bool(comparison.get('same_governance_required')) else 'no'} "
            + f"same_task={'yes' if bool(comparison.get('same_task')) else 'no'}",
            "transitions: "
            + f"failure={normalize_optional_string(comparison.get('failure_transition')) or 'unknown'} "
            + f"verification={normalize_optional_string(comparison.get('verification_transition')) or 'unknown'} "
            + f"reassessment={normalize_optional_string(comparison.get('reassessment_transition')) or 'unknown'} "
            + f"evaluation={normalize_optional_string(comparison.get('evaluation_transition')) or 'unknown'} "
            + f"governance={normalize_optional_string(comparison.get('governance_transition')) or 'unknown'} "
            + f"artifacts={normalize_optional_string(comparison.get('artifact_transition')) or 'unknown'}",
            "artifacts_left: "
            + f"expected={_format_text_list(left.get('expected_artifacts'))} "
            + f"produced={_format_text_list(left.get('produced_artifact_types'))}({int(left.get('produced_artifact_count', 0) or 0)}) "
            + f"baseline_status={normalize_optional_string(left.get('baseline_compare_status')) or 'none'} "
            + f"baseline_artifacts={_format_text_list(left.get('baseline_compared_artifact_types'))} "
            + f"status_counts={_format_status_counts(left.get('baseline_status_counts'))} "
            + f"missing_expected={'yes' if bool(left.get('missing_expected_artifact_warning')) else 'no'}",
            "artifacts_right: "
            + f"expected={_format_text_list(right.get('expected_artifacts'))} "
            + f"produced={_format_text_list(right.get('produced_artifact_types'))}({int(right.get('produced_artifact_count', 0) or 0)}) "
            + f"baseline_status={normalize_optional_string(right.get('baseline_compare_status')) or 'none'} "
            + f"baseline_artifacts={_format_text_list(right.get('baseline_compared_artifact_types'))} "
            + f"status_counts={_format_status_counts(right.get('baseline_status_counts'))} "
            + f"missing_expected={'yes' if bool(right.get('missing_expected_artifact_warning')) else 'no'}",
            _format_artifact_diff_line(left, right, comparison),
            "reason_code_diff: "
            + f"reassessment(+{_format_reason_codes(comparison.get('reassessment_reason_codes_added'))}; -{_format_reason_codes(comparison.get('reassessment_reason_codes_removed'))}) "
            + f"evaluation(+{_format_reason_codes(comparison.get('evaluation_reason_codes_added'))}; -{_format_reason_codes(comparison.get('evaluation_reason_codes_removed'))})",
            f"highlights: {_build_comparison_highlights(comparison)}",
        ]
    )


def _classify_failure_transition(
    left_manifest: Mapping[str, Any],
    right_manifest: Mapping[str, Any],
    left_failure: Mapping[str, Any],
    right_failure: Mapping[str, Any],
) -> str:
    left_status = normalize_optional_string(left_manifest.get("status")) or ""
    right_status = normalize_optional_string(right_manifest.get("status")) or ""
    left_failure_class = (
        normalize_optional_string(left_failure.get("failure_class")) or ""
    )
    right_failure_class = (
        normalize_optional_string(right_failure.get("failure_class")) or ""
    )

    left_effective_success = left_status == "success" and not left_failure_class
    right_effective_success = right_status == "success" and not right_failure_class

    if left_effective_success and not right_effective_success:
        return "regressed"
    if not left_effective_success and right_effective_success:
        return "resolved"
    if left_status == right_status and left_failure_class == right_failure_class:
        return "unchanged"
    return "changed"


def _classify_quality_boolean_transition(
    left_value: bool,
    right_value: bool,
    *,
    truthy_is_good: bool,
    improved_label: str,
    regressed_label: str,
) -> str:
    if left_value == right_value:
        return "unchanged"
    if truthy_is_good:
        return improved_label if right_value and not left_value else regressed_label
    return regressed_label if right_value and not left_value else improved_label


def _classify_risk_transition(
    left_level: str | None,
    right_level: str | None,
) -> str:
    left_normalized = normalize_optional_string(left_level) or ""
    right_normalized = normalize_optional_string(right_level) or ""
    if left_normalized == right_normalized:
        return "unchanged"
    if (
        left_normalized not in RISK_LEVEL_ORDER
        or right_normalized not in RISK_LEVEL_ORDER
    ):
        return "changed"
    if RISK_LEVEL_ORDER[right_normalized] > RISK_LEVEL_ORDER[left_normalized]:
        return "regressed"
    return "improved"


def _classify_evaluation_transition(
    left_evaluation: Mapping[str, Any],
    right_evaluation: Mapping[str, Any],
) -> str:
    left_requires_review = bool(left_evaluation.get("requires_human_review"))
    right_requires_review = bool(right_evaluation.get("requires_human_review"))
    left_recommendation = (
        normalize_optional_string(left_evaluation.get("recommendation")) or ""
    )
    right_recommendation = (
        normalize_optional_string(right_evaluation.get("recommendation")) or ""
    )

    if (
        left_requires_review == right_requires_review
        and left_recommendation == right_recommendation
    ):
        return "unchanged"
    if not left_requires_review and right_requires_review:
        return "regressed"
    if left_requires_review and not right_requires_review:
        return "improved"
    return "changed"


def _build_artifact_summary(
    *,
    task_contract: Mapping[str, Any],
    execution_result: Mapping[str, Any],
    verification_report: Mapping[str, Any],
    baseline_compare_results: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts_value = execution_result.get("artifacts")
    artifacts = list(artifacts_value) if isinstance(artifacts_value, list) else []
    produced_artifact_types = sorted(
        {
            artifact_type
            for artifact in artifacts
            if isinstance(artifact, Mapping)
            for artifact_type in [normalize_optional_string(artifact.get("type"))]
            if artifact_type
        }
    )
    warning_codes = _verification_warning_codes(verification_report)
    return {
        "expected_artifacts": normalize_string_list_sorted(
            task_contract.get("expected_artifacts")
        ),
        "produced_artifact_types": produced_artifact_types,
        "produced_artifact_count": len(artifacts),
        "baseline_compare_status": normalize_optional_string(
            baseline_compare_results.get("status")
        )
        or "",
        "baseline_compared_artifact_types": normalize_string_list_sorted(
            baseline_compare_results.get("compared_artifact_types")
        ),
        "baseline_status_counts": _normalize_status_counts(
            baseline_compare_results.get("status_counts")
        ),
        "missing_expected_artifact_warning": "missing_expected_artifact"
        in warning_codes,
    }


def _classify_artifact_transition(
    left_summary: Mapping[str, Any],
    right_summary: Mapping[str, Any],
) -> str:
    left_missing = bool(left_summary.get("missing_expected_artifact_warning"))
    right_missing = bool(right_summary.get("missing_expected_artifact_warning"))
    if left_missing != right_missing:
        return "regressed" if right_missing else "improved"

    left_score = _artifact_status_score(
        _extract_optional_mapping(left_summary, "baseline_status_counts")
    )
    right_score = _artifact_status_score(
        _extract_optional_mapping(right_summary, "baseline_status_counts")
    )
    if left_score != right_score:
        return "regressed" if right_score > left_score else "improved"

    if (
        normalize_string_list(left_summary.get("expected_artifacts"))
        == normalize_string_list(right_summary.get("expected_artifacts"))
        and normalize_string_list(left_summary.get("produced_artifact_types"))
        == normalize_string_list(right_summary.get("produced_artifact_types"))
        and int(left_summary.get("produced_artifact_count", 0) or 0)
        == int(right_summary.get("produced_artifact_count", 0) or 0)
        and normalize_optional_string(left_summary.get("baseline_compare_status"))
        == normalize_optional_string(right_summary.get("baseline_compare_status"))
        and normalize_string_list(left_summary.get("baseline_compared_artifact_types"))
        == normalize_string_list(right_summary.get("baseline_compared_artifact_types"))
        and _normalize_status_counts(left_summary.get("baseline_status_counts"))
        == _normalize_status_counts(right_summary.get("baseline_status_counts"))
    ):
        return "unchanged"
    return "changed"


def _artifact_status_score(status_counts: Mapping[str, Any]) -> int:
    normalized = _normalize_status_counts(status_counts)
    return (
        int(normalized.get("warning", 0) or 0)
        + int(normalized.get("breaking", 0) or 0) * 2
        + int(normalized.get("error", 0) or 0) * 2
    )


def _list_added_items(left_values: list[str], right_values: list[str]) -> list[str]:
    left_set = set(left_values)
    return [value for value in right_values if value not in left_set]


def _list_removed_items(left_values: list[str], right_values: list[str]) -> list[str]:
    right_set = set(right_values)
    return [value for value in left_values if value not in right_set]


def _build_comparison_highlights(comparison: Mapping[str, Any]) -> str:
    highlights: list[str] = []
    for field_name, label in (
        ("failure_transition", "failure"),
        ("verification_transition", "verification"),
        ("reassessment_transition", "risk"),
        ("evaluation_transition", "evaluation"),
        ("governance_transition", "governance"),
        ("artifact_transition", "artifacts"),
    ):
        transition = normalize_optional_string(comparison.get(field_name)) or "unknown"
        if transition != "unchanged":
            highlights.append(f"{label} {transition}")

    reassessment_reason_delta = _format_reason_code_delta(
        comparison.get("reassessment_reason_codes_added"),
        comparison.get("reassessment_reason_codes_removed"),
    )
    if reassessment_reason_delta:
        highlights.append(f"reassessment reasons {reassessment_reason_delta}")

    evaluation_reason_delta = _format_reason_code_delta(
        comparison.get("evaluation_reason_codes_added"),
        comparison.get("evaluation_reason_codes_removed"),
    )
    if evaluation_reason_delta:
        highlights.append(f"evaluation reasons {evaluation_reason_delta}")

    artifact_expected_delta = _format_text_delta(
        comparison.get("expected_artifacts_added"),
        comparison.get("expected_artifacts_removed"),
    )
    if artifact_expected_delta:
        highlights.append(f"expected artifacts {artifact_expected_delta}")

    artifact_produced_delta = _format_text_delta(
        comparison.get("produced_artifact_types_added"),
        comparison.get("produced_artifact_types_removed"),
    )
    if artifact_produced_delta:
        highlights.append(f"produced artifacts {artifact_produced_delta}")

    artifact_baseline_delta = _format_text_delta(
        comparison.get("baseline_compared_artifact_types_added"),
        comparison.get("baseline_compared_artifact_types_removed"),
    )
    if artifact_baseline_delta:
        highlights.append(f"baseline artifacts {artifact_baseline_delta}")

    if not highlights:
        return "no material changes"
    return "; ".join(highlights)


def _format_text_delta(
    added_values: object | None,
    removed_values: object | None,
) -> str:
    parts: list[str] = []
    added_values_list = normalize_string_list(added_values)
    removed_values_list = normalize_string_list(removed_values)
    if added_values_list:
        parts.append("+" + ",".join(added_values_list))
    if removed_values_list:
        parts.append("-" + ",".join(removed_values_list))
    return " ".join(parts)


def _format_reason_code_delta(
    added_values: object | None,
    removed_values: object | None,
) -> str:
    return _format_text_delta(added_values, removed_values)


def _format_named_delta(
    label: str,
    added_values: object | None,
    removed_values: object | None,
) -> str:
    delta = _format_text_delta(added_values, removed_values)
    if not delta:
        return ""
    added_values_list = normalize_string_list(added_values)
    removed_values_list = normalize_string_list(removed_values)
    added_text = ",".join(added_values_list) if added_values_list else "none"
    removed_text = ",".join(removed_values_list) if removed_values_list else "none"
    return f"{label}(+{added_text}; -{removed_text})"


def _format_artifact_diff_line(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> str:
    parts = [
        "artifact_diff: "
        + f"transition={normalize_optional_string(comparison.get('artifact_transition')) or 'unknown'}"
    ]
    for segment in (
        _format_named_delta(
            "expected",
            comparison.get("expected_artifacts_added"),
            comparison.get("expected_artifacts_removed"),
        ),
        _format_named_delta(
            "produced",
            comparison.get("produced_artifact_types_added"),
            comparison.get("produced_artifact_types_removed"),
        ),
        _format_named_delta(
            "baseline",
            comparison.get("baseline_compared_artifact_types_added"),
            comparison.get("baseline_compared_artifact_types_removed"),
        ),
    ):
        if segment:
            parts.append(segment)
    parts.append(
        "status_counts("
        + f"left={_format_status_counts(left.get('baseline_status_counts'))} "
        + f"right={_format_status_counts(right.get('baseline_status_counts'))})"
    )
    parts.append(
        "missing_expected="
        + f"{'yes' if bool(left.get('missing_expected_artifact_warning')) else 'no'}"
        + "->"
        + f"{'yes' if bool(right.get('missing_expected_artifact_warning')) else 'no'}"
    )
    return " ".join(parts)


def _format_text_list(values: object | None) -> str:
    normalized = normalize_string_list(values)
    if not normalized:
        return "none"
    return ",".join(normalized)


def _format_status_counts(values: object | None) -> str:
    normalized = _normalize_status_counts(values)
    if not normalized:
        return "none"
    return ",".join(f"{key}:{normalized[key]}" for key in sorted(normalized))


def _format_reason_codes(values: object | None) -> str:
    return _format_text_list(values)


def _verification_warning_codes(verification_report: Mapping[str, Any]) -> list[str]:
    return sorted(
        {
            warning_code
            for warning in verification_report.get("warnings", [])
            if isinstance(warning, Mapping)
            for warning_code in [normalize_optional_string(warning.get("code"))]
            if warning_code
        }
    )


def _read_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return dict(payload)


def _extract_optional_mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _normalize_status_counts(value: object | None) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        key = normalize_optional_string(raw_key)
        if not key:
            continue
        try:
            normalized[key] = int(raw_count)
        except (TypeError, ValueError):
            continue
    return normalized
