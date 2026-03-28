from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
import json


class BaselineComparator:
    """Compare a current artifact against a single baseline JSON artifact.

    This is intentionally a small comparison tool:
    - it reads only explicitly requested baseline files
    - it compares structure and a few critical fields
    - it classifies drift as compatible, warning, or breaking
    - it does not make automatic pass/fail decisions for the runtime
    """

    SUPPORTED_ARTIFACT_TYPES = {
        "verification_report",
        "residual_followup",
        "metrics_summary",
        "event_trace",
        "journal_append_trace",
    }

    FORBIDDEN_JOURNAL_KEYS = {
        "state_writeback_payload",
        "sandbox_result",
        "rollback_result",
        "execution_result",
        "snapshot_ref",
        "restored_state",
        "full_log",
        "environment_dump",
    }

    def load_baseline(self, path: str | Path) -> dict[str, Any]:
        baseline_path = Path(path)
        if baseline_path.suffix.lower() != ".json":
            return {
                "status": "error",
                "path": str(baseline_path),
                "data": None,
                "summary": "Baseline load failed: only explicitly specified .json files are supported.",
                "reason_codes": ["unsupported_extension"],
            }

        try:
            payload = baseline_path.read_text(encoding="utf-8")
        except OSError as exc:
            return {
                "status": "error",
                "path": str(baseline_path),
                "data": None,
                "summary": f"Baseline load failed: {exc}.",
                "reason_codes": ["path_not_readable"],
            }

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            return {
                "status": "error",
                "path": str(baseline_path),
                "data": None,
                "summary": f"Baseline load failed: invalid JSON ({exc.msg}).",
                "reason_codes": ["invalid_json"],
            }

        return {
            "status": "ok",
            "path": str(baseline_path),
            "data": data,
            "summary": f"Loaded baseline JSON from {baseline_path.name}.",
            "reason_codes": [],
        }

    def compare(
        self,
        current: Mapping[str, Any] | Sequence[Any],
        baseline: Mapping[str, Any] | Sequence[Any],
        *,
        artifact_type: str,
    ) -> dict[str, Any]:
        normalized_artifact_type = self._normalize_artifact_type(artifact_type)
        required_fields = self._required_top_level_fields(normalized_artifact_type)

        missing_fields: list[str] = []
        unexpected_fields: list[str] = []
        type_mismatches: list[dict[str, str]] = []
        value_drifts: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        status = "compatible"

        if not isinstance(current, Mapping):
            type_mismatches.append(
                {
                    "field": "$",
                    "expected": "object",
                    "current": self._type_label(current),
                }
            )
            reason_codes.append("current_root_type_mismatch")
            status = "breaking"
            result = self._build_diff_result(
                artifact_type=normalized_artifact_type,
                status=status,
                missing_fields=missing_fields,
                unexpected_fields=unexpected_fields,
                type_mismatches=type_mismatches,
                value_drifts=value_drifts,
                reason_codes=reason_codes,
            )
            result["summary"] = self.summarize_diff(result)
            return result

        if not isinstance(baseline, Mapping):
            type_mismatches.append(
                {
                    "field": "$",
                    "expected": "object",
                    "current": self._type_label(baseline),
                }
            )
            reason_codes.append("baseline_root_type_mismatch")
            status = "breaking"
            result = self._build_diff_result(
                artifact_type=normalized_artifact_type,
                status=status,
                missing_fields=missing_fields,
                unexpected_fields=unexpected_fields,
                type_mismatches=type_mismatches,
                value_drifts=value_drifts,
                reason_codes=reason_codes,
            )
            result["summary"] = self.summarize_diff(result)
            return result

        baseline_fields = set(str(key) for key in baseline.keys())
        current_fields = set(str(key) for key in current.keys())
        missing_fields = sorted(baseline_fields - current_fields)
        unexpected_fields = sorted(current_fields - baseline_fields)

        required_missing = sorted(set(required_fields) & set(missing_fields))
        if required_missing:
            reason_codes.append("missing_required_fields")
            status = self._escalate(status, "breaking")
        elif missing_fields:
            reason_codes.append("missing_optional_fields")
            status = self._escalate(status, "warning")

        if unexpected_fields:
            reason_codes.append("unexpected_fields_present")
            status = self._escalate(status, "warning")

        path_type_mismatches = self._compare_key_path_types(
            current=current,
            baseline=baseline,
            artifact_type=normalized_artifact_type,
        )
        if path_type_mismatches:
            type_mismatches.extend(path_type_mismatches)
            reason_codes.append("type_mismatch_detected")
            status = self._escalate(status, "breaking")

        specific = self._artifact_specific_diff(
            current=current,
            baseline=baseline,
            artifact_type=normalized_artifact_type,
        )
        value_drifts.extend(specific["value_drifts"])
        reason_codes.extend(code for code in specific["reason_codes"] if code not in reason_codes)
        status = self._escalate(status, specific["status"])

        result = self._build_diff_result(
            artifact_type=normalized_artifact_type,
            status=status,
            missing_fields=missing_fields,
            unexpected_fields=unexpected_fields,
            type_mismatches=type_mismatches,
            value_drifts=value_drifts,
            reason_codes=reason_codes,
        )
        result["summary"] = self.summarize_diff(result)
        return result

    def compare_bundle_artifact(
        self,
        bundle: object,
        baseline: Mapping[str, Any] | Sequence[Any],
        *,
        artifact_type: str,
    ) -> dict[str, Any]:
        from harness.evaluation.evaluation_input import to_baseline_artifacts

        artifacts = to_baseline_artifacts(bundle)
        normalized_artifact_type = self._normalize_artifact_type(artifact_type)
        return self.compare(
            current=artifacts[normalized_artifact_type],
            baseline=baseline,
            artifact_type=normalized_artifact_type,
        )

    def summarize_diff(self, diff_result: Mapping[str, Any]) -> str:
        artifact_type = str(diff_result.get("artifact_type") or "artifact")
        status = str(diff_result.get("status") or "warning")
        if status == "compatible":
            return f"{artifact_type} is compatible with the baseline."

        segments: list[str] = []
        missing_fields = list(diff_result.get("missing_fields", []))
        unexpected_fields = list(diff_result.get("unexpected_fields", []))
        type_mismatches = list(diff_result.get("type_mismatches", []))
        value_drifts = list(diff_result.get("value_drifts", []))

        if missing_fields:
            segments.append(f"missing fields: {', '.join(str(field) for field in missing_fields[:3])}")
        if unexpected_fields:
            segments.append(
                f"unexpected fields: {', '.join(str(field) for field in unexpected_fields[:3])}"
            )
        if type_mismatches:
            mismatch = type_mismatches[0]
            segments.append(
                "type mismatch at "
                f"{mismatch['field']} ({mismatch['expected']} vs {mismatch['current']})"
            )
        if value_drifts:
            drift = value_drifts[0]
            segments.append(f"value drift at {drift['field']}: {drift['detail']}")

        detail = "; ".join(segments) if segments else "drift detected without a more specific detail"
        return f"{artifact_type} is {status}: {detail}."

    def is_structurally_compatible(
        self,
        current: Mapping[str, Any] | Sequence[Any],
        baseline: Mapping[str, Any] | Sequence[Any],
        *,
        artifact_type: str,
    ) -> bool:
        diff_result = self.compare(current, baseline, artifact_type=artifact_type)
        return not diff_result["missing_fields"] and not diff_result["type_mismatches"]

    def _artifact_specific_diff(
        self,
        *,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
        artifact_type: str,
    ) -> dict[str, Any]:
        handlers = {
            "verification_report": self._compare_verification_report,
            "residual_followup": self._compare_residual_followup,
            "metrics_summary": self._compare_metrics_summary,
            "event_trace": self._compare_event_trace,
            "journal_append_trace": self._compare_journal_append_trace,
        }
        return handlers[artifact_type](current, baseline)

    def _compare_verification_report(
        self,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
    ) -> dict[str, Any]:
        value_drifts: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        status = "compatible"

        value_drifts.extend(
            self._compare_simple_value(
                current=current,
                baseline=baseline,
                path="status",
                detail_template="status changed from {baseline} to {current}",
            )
        )
        value_drifts.extend(
            self._compare_simple_value(
                current=current,
                baseline=baseline,
                path="passed",
                detail_template="passed changed from {baseline} to {current}",
            )
        )
        value_drifts.extend(
            self._compare_list_length(
                current=current,
                baseline=baseline,
                path="issues",
                detail_template="issues count changed from {baseline} to {current}",
            )
        )
        value_drifts.extend(
            self._compare_list_length(
                current=current,
                baseline=baseline,
                path="warnings",
                detail_template="warnings count changed from {baseline} to {current}",
            )
        )
        if value_drifts:
            reason_codes.append("verification_value_drift")
            status = "warning"
        return {
            "status": status,
            "value_drifts": value_drifts,
            "reason_codes": reason_codes,
        }

    def _compare_residual_followup(
        self,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
    ) -> dict[str, Any]:
        value_drifts: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        status = "compatible"

        value_drifts.extend(
            self._compare_simple_value(
                current=current,
                baseline=baseline,
                path="reassessment.reassessed_level",
                detail_template="residual risk changed from {baseline} to {current}",
            )
        )
        value_drifts.extend(
            self._compare_simple_value(
                current=current,
                baseline=baseline,
                path="telemetry_payload.followup_required",
                detail_template="followup_required changed from {baseline} to {current}",
            )
        )
        value_drifts.extend(
            self._compare_simple_value(
                current=current,
                baseline=baseline,
                path="telemetry_payload.governance_required",
                detail_template="governance_required changed from {baseline} to {current}",
            )
        )

        current_auto_execution = self._get_path_value(current, "auto_execution")
        if current_auto_execution["exists"] and current_auto_execution["value"] != "none":
            value_drifts.append(
                {
                    "field": "auto_execution",
                    "baseline": self._get_path_value(baseline, "auto_execution")["value"],
                    "current": current_auto_execution["value"],
                    "detail": "advice is no longer advisory-only",
                }
            )
            reason_codes.append("advisory_boundary_broken")
            status = "breaking"
        elif value_drifts:
            reason_codes.append("residual_value_drift")
            status = "warning"

        return {
            "status": status,
            "value_drifts": value_drifts,
            "reason_codes": reason_codes,
        }

    def _compare_metrics_summary(
        self,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
    ) -> dict[str, Any]:
        value_drifts: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        status = "compatible"
        metric_names = [
            "retry_count",
            "rollback_count",
            "human_handoff_count",
            "tool_misuse_count",
        ]
        for metric_name in metric_names:
            value_drifts.extend(
                self._compare_simple_value(
                    current=current,
                    baseline=baseline,
                    path=f"metrics.{metric_name}.last",
                    detail_template=f"{metric_name} changed from {{baseline}} to {{current}}",
                )
            )
        if value_drifts:
            reason_codes.append("metrics_value_drift")
            status = "warning"
        return {
            "status": status,
            "value_drifts": value_drifts,
            "reason_codes": reason_codes,
        }

    def _compare_event_trace(
        self,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
    ) -> dict[str, Any]:
        value_drifts: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        status = "compatible"

        baseline_names = self._event_names(baseline.get("dispatch_trace"))
        current_names = self._event_names(current.get("dispatch_trace"))
        missing_events = [name for name in baseline_names if name not in current_names]
        if missing_events:
            value_drifts.append(
                {
                    "field": "dispatch_trace.event_name",
                    "baseline": baseline_names,
                    "current": current_names,
                    "detail": f"missing expected events: {', '.join(missing_events)}",
                }
            )
            reason_codes.append("missing_expected_events")
            status = "breaking"
        elif not self._is_subsequence(baseline_names, current_names):
            value_drifts.append(
                {
                    "field": "dispatch_trace.event_name",
                    "baseline": baseline_names,
                    "current": current_names,
                    "detail": "event order changed from the baseline sequence",
                }
            )
            reason_codes.append("event_order_changed")
            status = "breaking"

        unexpected_events = [name for name in current_names if name not in baseline_names]
        if unexpected_events:
            value_drifts.append(
                {
                    "field": "dispatch_trace.event_name",
                    "baseline": baseline_names,
                    "current": current_names,
                    "detail": f"additional events observed: {', '.join(unexpected_events)}",
                }
            )
            if "unexpected_events_present" not in reason_codes:
                reason_codes.append("unexpected_events_present")
            status = self._escalate(status, "warning")

        return {
            "status": status,
            "value_drifts": value_drifts,
            "reason_codes": reason_codes,
        }

    def _compare_journal_append_trace(
        self,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
    ) -> dict[str, Any]:
        value_drifts: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        status = "compatible"

        current_names = self._event_names(current.get("dispatch_trace"))
        if "on_journal_append" not in current_names:
            value_drifts.append(
                {
                    "field": "dispatch_trace.event_name",
                    "baseline": self._event_names(baseline.get("dispatch_trace")),
                    "current": current_names,
                    "detail": "missing required event on_journal_append",
                }
            )
            reason_codes.append("journal_append_missing")
            status = "breaking"

        forbidden_keys = sorted(self._find_forbidden_keys(current))
        if forbidden_keys:
            value_drifts.append(
                {
                    "field": "journal_entry",
                    "baseline": [],
                    "current": forbidden_keys,
                    "detail": f"forbidden mirrored fields detected: {', '.join(forbidden_keys)}",
                }
            )
            reason_codes.append("journal_payload_bloat_detected")
            status = "breaking"

        payload = current.get("payload")
        if isinstance(payload, Mapping):
            payload_missing = [
                field
                for field in [
                    "event_id",
                    "timestamp",
                    "task_id",
                    "contract_id",
                    "schema_version",
                    "lesson_entry",
                    "source",
                ]
                if field not in payload
            ]
            if payload_missing:
                value_drifts.append(
                    {
                        "field": "payload",
                        "baseline": "complete",
                        "current": payload_missing,
                        "detail": f"payload missing fields: {', '.join(payload_missing)}",
                    }
                )
                reason_codes.append("journal_payload_incomplete")
                status = "breaking"

        return {
            "status": status,
            "value_drifts": value_drifts,
            "reason_codes": reason_codes,
        }

    def _compare_key_path_types(
        self,
        *,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
        artifact_type: str,
    ) -> list[dict[str, str]]:
        mismatches: list[dict[str, str]] = []
        for path in self._required_key_paths(artifact_type):
            baseline_value = self._get_path_value(baseline, path)
            current_value = self._get_path_value(current, path)
            if not baseline_value["exists"] or not current_value["exists"]:
                continue
            if not self._types_compatible(current_value["value"], baseline_value["value"]):
                mismatches.append(
                    {
                        "field": path,
                        "expected": self._type_label(baseline_value["value"]),
                        "current": self._type_label(current_value["value"]),
                    }
                )
        return mismatches

    def _compare_simple_value(
        self,
        *,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
        path: str,
        detail_template: str,
    ) -> list[dict[str, Any]]:
        baseline_value = self._get_path_value(baseline, path)
        current_value = self._get_path_value(current, path)
        if not baseline_value["exists"] or not current_value["exists"]:
            return []
        if current_value["value"] == baseline_value["value"]:
            return []
        return [
            {
                "field": path,
                "baseline": baseline_value["value"],
                "current": current_value["value"],
                "detail": detail_template.format(
                    baseline=baseline_value["value"],
                    current=current_value["value"],
                ),
            }
        ]

    def _compare_list_length(
        self,
        *,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
        path: str,
        detail_template: str,
    ) -> list[dict[str, Any]]:
        baseline_value = self._get_path_value(baseline, path)
        current_value = self._get_path_value(current, path)
        if not baseline_value["exists"] or not current_value["exists"]:
            return []
        if not isinstance(baseline_value["value"], Sequence) or isinstance(
            baseline_value["value"],
            (str, bytes, bytearray),
        ):
            return []
        if not isinstance(current_value["value"], Sequence) or isinstance(
            current_value["value"],
            (str, bytes, bytearray),
        ):
            return []
        baseline_size = len(baseline_value["value"])
        current_size = len(current_value["value"])
        if baseline_size == current_size:
            return []
        return [
            {
                "field": path,
                "baseline": baseline_size,
                "current": current_size,
                "detail": detail_template.format(baseline=baseline_size, current=current_size),
            }
        ]

    def _required_top_level_fields(self, artifact_type: str) -> set[str]:
        mapping = {
            "verification_report": {"status", "passed", "issues", "warnings"},
            "residual_followup": {"status", "reassessment", "telemetry_payload", "governance", "auto_execution"},
            "metrics_summary": {"event_count", "metric_count", "metrics"},
            "event_trace": {"dispatch_trace"},
            "journal_append_trace": {"dispatch_trace", "journal_entry", "learning_journal"},
        }
        return mapping[artifact_type]

    def _required_key_paths(self, artifact_type: str) -> list[str]:
        mapping = {
            "verification_report": [
                "status",
                "passed",
                "issues",
                "warnings",
            ],
            "residual_followup": [
                "status",
                "reassessment.reassessed_level",
                "telemetry_payload.followup_required",
                "telemetry_payload.governance_required",
                "auto_execution",
            ],
            "metrics_summary": [
                "event_count",
                "metric_count",
                "metrics.retry_count.last",
                "metrics.rollback_count.last",
                "metrics.human_handoff_count.last",
                "metrics.tool_misuse_count.last",
            ],
            "event_trace": [
                "dispatch_trace",
            ],
            "journal_append_trace": [
                "dispatch_trace",
                "journal_entry.entry_id",
                "journal_entry.task_id",
                "journal_entry.task_type",
                "journal_entry.tags",
                "journal_entry.lesson",
                "journal_entry.source",
                "journal_entry.confidence",
                "journal_entry.created_at",
                "learning_journal.status",
            ],
        }
        return mapping[artifact_type]

    def _event_names(self, dispatch_trace: Any) -> list[str]:
        if not isinstance(dispatch_trace, Sequence) or isinstance(dispatch_trace, (str, bytes, bytearray)):
            return []
        event_names: list[str] = []
        for item in dispatch_trace:
            if not isinstance(item, Mapping):
                continue
            event_name = str(item.get("event_name") or "").strip()
            if event_name:
                event_names.append(event_name)
        return event_names

    def _is_subsequence(self, expected: Sequence[str], observed: Sequence[str]) -> bool:
        if not expected:
            return True
        index = 0
        for item in observed:
            if item == expected[index]:
                index += 1
                if index == len(expected):
                    return True
        return False

    def _find_forbidden_keys(self, value: Any, *, prefix: str = "") -> set[str]:
        found: set[str] = set()
        if isinstance(value, Mapping):
            for key, nested in value.items():
                normalized_key = str(key)
                if normalized_key in self.FORBIDDEN_JOURNAL_KEYS:
                    found.add(prefix + normalized_key if prefix else normalized_key)
                nested_prefix = f"{prefix}{normalized_key}." if prefix else f"{normalized_key}."
                found.update(self._find_forbidden_keys(nested, prefix=nested_prefix))
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for nested in value:
                found.update(self._find_forbidden_keys(nested, prefix=prefix))
        return found

    def _get_path_value(self, payload: Mapping[str, Any], path: str) -> dict[str, Any]:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return {"exists": False, "value": None}
            current = current[part]
        return {"exists": True, "value": current}

    def _types_compatible(self, current: Any, baseline: Any) -> bool:
        if isinstance(current, bool) or isinstance(baseline, bool):
            return isinstance(current, bool) and isinstance(baseline, bool)
        if self._is_number(current) and self._is_number(baseline):
            return True
        if (
            isinstance(current, Sequence)
            and not isinstance(current, (str, bytes, bytearray))
            and isinstance(baseline, Sequence)
            and not isinstance(baseline, (str, bytes, bytearray))
        ):
            return True
        return isinstance(current, type(baseline))

    def _is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _type_label(self, value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if self._is_number(value):
            return "number"
        if isinstance(value, Mapping):
            return "object"
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return "array"
        return type(value).__name__

    def _normalize_artifact_type(self, artifact_type: str) -> str:
        normalized = str(artifact_type).strip().lower()
        if normalized not in self.SUPPORTED_ARTIFACT_TYPES:
            raise ValueError(f"unsupported artifact_type: {artifact_type}")
        return normalized

    def _build_diff_result(
        self,
        *,
        artifact_type: str,
        status: str,
        missing_fields: list[str],
        unexpected_fields: list[str],
        type_mismatches: list[dict[str, str]],
        value_drifts: list[dict[str, Any]],
        reason_codes: list[str],
    ) -> dict[str, Any]:
        return {
            "artifact_type": artifact_type,
            "status": status,
            "missing_fields": missing_fields,
            "unexpected_fields": unexpected_fields,
            "type_mismatches": type_mismatches,
            "value_drifts": value_drifts,
            "summary": "",
            "reason_codes": reason_codes,
        }

    def _escalate(self, current: str, candidate: str) -> str:
        ranking = {
            "compatible": 0,
            "warning": 1,
            "breaking": 2,
        }
        if ranking[candidate] > ranking[current]:
            return candidate
        return current

