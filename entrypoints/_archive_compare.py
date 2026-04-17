from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from entrypoints._utils import (
    extract_mapping,
    normalize_optional_string,
    normalize_string_list,
    normalize_string_list_sorted,
)
from entrypoints._archive_reader import (
    _extract_optional_mapping,
    _normalize_status_counts,
)

RISK_LEVEL_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
}


def compare_run_archives(
    archive_root: str | Path,
    left_run_id: str,
    right_run_id: str,
) -> dict[str, Any]:
    # Import here to avoid circular import; archive_browse is the public facade
    from entrypoints._archive_reader import _load_archive_entries, _read_archive_record
    from entrypoints._archive_filter import _find_archive_entry_by_run_id

    def _find(run_id: str) -> dict[str, Any]:
        archive_root_path = Path(archive_root)
        entries, source = _load_archive_entries(archive_root_path)
        rid = normalize_optional_string(run_id)
        if not rid:
            raise ValueError("run_id must not be empty")
        entry = _find_archive_entry_by_run_id(entries, rid)
        if entry is None:
            raise LookupError(f"run_id not found: {rid}")
        return {
            "archive_root": str(archive_root_path),
            "index_file": str(archive_root_path / "index.jsonl"),
            "entry": entry,
            "archive": _read_archive_record(Path(entry["archive_dir"])),
            "source": source,
        }

    left_payload = _find(left_run_id)
    right_payload = _find(right_run_id)

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
