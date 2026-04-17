from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from entrypoints._utils import (
    extract_mapping,
    normalize_optional_string,
    normalize_string_list,
)
from entrypoints._archive_reader import (
    _extract_optional_mapping,
    _normalize_status_counts,
)


def build_summarize_payload(
    archive_root_path: Path,
    filtered_entries: list[dict[str, Any]],
    filters: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    """Construct the dict returned by summarize_run_archives."""
    return {
        "archive_root": str(archive_root_path),
        "index_file": str(archive_root_path / "index.jsonl"),
        "entry_count": len(filtered_entries),
        "filters": filters,
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
                for e in filtered_entries
                if bool(e.get("missing_expected_artifact_warning"))
            ),
            "no": sum(
                1
                for e in filtered_entries
                if not bool(e.get("missing_expected_artifact_warning"))
            ),
        },
        "source": source,
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
    from entrypoints._archive_compare import _build_artifact_summary

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
