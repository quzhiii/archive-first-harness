from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any


EVENT_TRACE_KEY_EVENTS = (
    "on_verification_report",
    "on_residual_followup",
    "on_governance_check",
    "on_sandbox_required",
    "on_journal_append",
)

JOURNAL_APPEND_REQUIRED_PAYLOAD_FIELDS = {
    "event_id",
    "timestamp",
    "task_id",
    "contract_id",
    "schema_version",
    "lesson_entry",
    "source",
}

FORBIDDEN_JOURNAL_TRACE_KEYS = {
    "state_writeback_payload",
    "sandbox_result",
    "rollback_result",
    "execution_result",
    "snapshot_ref",
    "restored_state",
    "full_log",
    "environment_dump",
}


@dataclass(slots=True)
class EvaluationInputBundle:
    """Hold the evaluator input surface on one stable, explicit schema.

    Boundary rules:
    - `verification_report`, `residual_followup`, `metrics_summary`, and
      `block_selection_report` stay as structured artifacts.
    - `event_trace` and `journal_append_trace` are converted into summaries before
      entering the bundle, so evaluators do not consume raw hook history dumps.
    - `task_contract_summary` is intentionally smaller than the full contract and does
      not mirror tools, policies, or full runtime configuration.
    """

    task_contract_summary: dict[str, Any]
    block_selection_report: dict[str, Any]
    verification_report: dict[str, Any] | None
    residual_followup: dict[str, Any] | None
    metrics_summary: dict[str, Any] | None
    event_trace_summary: dict[str, Any]
    journal_append_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_contract_summary": _deep_copy_mapping(self.task_contract_summary),
            "block_selection_report": _deep_copy_mapping(self.block_selection_report),
            "verification_report": _deep_copy_optional_mapping(self.verification_report),
            "residual_followup": _deep_copy_optional_mapping(self.residual_followup),
            "metrics_summary": _deep_copy_optional_mapping(self.metrics_summary),
            "event_trace_summary": _deep_copy_mapping(self.event_trace_summary),
            "journal_append_summary": _deep_copy_mapping(self.journal_append_summary),
        }


def build_evaluation_input_bundle(
    *,
    task_contract: object,
    block_selection_report: Mapping[str, Any] | None = None,
    verification_report: Mapping[str, Any] | None = None,
    residual_followup: Mapping[str, Any] | None = None,
    metrics_summary: Mapping[str, Any] | None = None,
    event_trace: Mapping[str, Any] | Sequence[Any] | None = None,
    journal_append_trace: Mapping[str, Any] | Sequence[Any] | None = None,
) -> EvaluationInputBundle:
    if task_contract is None:
        raise ValueError("task_contract is required to build an evaluation input bundle")

    return EvaluationInputBundle(
        task_contract_summary=summarize_task_contract(task_contract),
        block_selection_report=_normalize_block_selection_report(block_selection_report),
        verification_report=_deep_copy_optional_mapping(verification_report),
        residual_followup=_deep_copy_optional_mapping(residual_followup),
        metrics_summary=_deep_copy_optional_mapping(metrics_summary),
        event_trace_summary=summarize_event_trace(event_trace),
        journal_append_summary=summarize_journal_append_trace(journal_append_trace),
    )


def summarize_task_contract(task_contract: object) -> dict[str, Any]:
    payload = _to_plain_data(task_contract)
    if not isinstance(payload, Mapping):
        raise TypeError("task_contract must be a mapping or dataclass-like object")

    task_id = _as_string(payload.get("task_id"))
    contract_id = _as_string(payload.get("contract_id"))
    task_type = _as_string(payload.get("task_type"))
    goal = _as_string(payload.get("goal"))
    success_criteria = _normalize_string_list(payload.get("success_criteria"), limit=3)
    expected_artifacts = _normalize_string_list(payload.get("expected_artifacts"), limit=3)
    stop_conditions = _normalize_string_list(payload.get("stop_conditions"), limit=3)
    write_permission_level = _as_string(payload.get("write_permission_level"))
    residual_risk_level = _as_string(payload.get("residual_risk_level"))
    methodology_family = _as_string(payload.get("methodology_family"))

    scenario_tags = [
        tag
        for tag in [
            task_type,
            f"risk:{residual_risk_level}" if residual_risk_level else "",
            f"permission:{write_permission_level}" if write_permission_level else "",
            f"method:{methodology_family}" if methodology_family else "",
        ]
        if tag
    ]

    return {
        "task_id": task_id,
        "contract_id": contract_id,
        "task_type": task_type,
        "goal": goal,
        "success_criteria": success_criteria,
        "expected_artifacts": expected_artifacts,
        "stop_conditions": stop_conditions,
        "scenario_tags": scenario_tags,
        "constraint_flags": {
            "has_stop_conditions": bool(stop_conditions),
            "write_capable": write_permission_level in {"write", "destructive_write"},
            "elevated_residual_risk": residual_risk_level in {"medium", "high"},
        },
    }


def summarize_event_trace(
    event_trace: Mapping[str, Any] | Sequence[Any] | None,
) -> dict[str, Any]:
    entries = _extract_trace_entries(event_trace)
    event_sequence = [_as_string(entry.get("event_name")) for entry in entries if _as_string(entry.get("event_name"))]
    event_types = _ordered_unique(event_sequence)
    status_counts = _count_labels(
        [_as_string(entry.get("status")).lower() for entry in entries if _as_string(entry.get("status"))]
    )
    error_count = sum(
        count
        for status, count in status_counts.items()
        if "error" in status or "fail" in status
    )
    warning_count = sum(
        count
        for status, count in status_counts.items()
        if "warn" in status
    )
    last_timestamp = ""
    for entry in reversed(entries):
        timestamp = _as_string(entry.get("timestamp"))
        if timestamp:
            last_timestamp = timestamp
            break

    return {
        "event_count": len(entries),
        "event_sequence": event_sequence,
        "event_types": event_types,
        "key_events": {
            event_name: event_name in event_sequence
            for event_name in EVENT_TRACE_KEY_EVENTS
        },
        "status_counts": status_counts,
        "error_count": error_count,
        "warning_count": warning_count,
        "status_hint": _trace_status_hint(error_count=error_count, event_count=len(entries)),
        "last_timestamp": last_timestamp,
    }


def summarize_journal_append_trace(
    journal_append_trace: Mapping[str, Any] | Sequence[Any] | None,
) -> dict[str, Any]:
    payload = _to_plain_data(journal_append_trace)
    entries = _extract_trace_entries(payload)
    event_sequence = [_as_string(entry.get("event_name")) for entry in entries if _as_string(entry.get("event_name"))]
    append_count = sum(1 for event_name in event_sequence if event_name == "on_journal_append")

    payload_mapping = payload if isinstance(payload, Mapping) else {}
    append_payload = payload_mapping.get("payload")
    if not isinstance(append_payload, Mapping):
        append_payload = {}
    journal_entry = payload_mapping.get("journal_entry")
    if not isinstance(journal_entry, Mapping):
        journal_entry = {}
    learning_journal = payload_mapping.get("learning_journal")
    if not isinstance(learning_journal, Mapping):
        learning_journal = {}

    source_candidates = [
        _as_string(append_payload.get("source")),
        _as_string(journal_entry.get("source")),
        _as_string(learning_journal.get("written_source")),
    ]
    written_entry_ids = _ordered_unique(
        [
            value
            for value in [
                _as_string(journal_entry.get("entry_id")),
                _as_string(learning_journal.get("written_entry_id")),
            ]
            if value
        ]
    )

    lesson_tags = _normalize_string_list(journal_entry.get("tags"))
    confidence_values = [
        value
        for value in [
            _safe_float(journal_entry.get("confidence")),
            _safe_float(_mapping_get(journal_entry, "lesson_entry.confidence")),
            _safe_float(_mapping_get(append_payload, "lesson_entry.confidence")),
        ]
        if value is not None
    ]
    archive_statuses = _ordered_unique(
        [
            value
            for value in [
                _as_string(journal_entry.get("archive_status")).lower(),
                _as_string(_mapping_get(append_payload, "lesson_entry.archive_status")).lower(),
            ]
            if value
        ]
    )

    lesson_preview = _shorten_text(
        _as_string(journal_entry.get("lesson"))
        or _as_string(_mapping_get(append_payload, "lesson_entry.lesson"))
    )
    last_timestamp = ""
    for entry in reversed(entries):
        timestamp = _as_string(entry.get("timestamp"))
        if timestamp:
            last_timestamp = timestamp
            break
    if not last_timestamp:
        last_timestamp = _as_string(append_payload.get("timestamp"))

    forbidden_mirrored_fields = sorted(_find_forbidden_keys(payload_mapping))
    payload_fields_complete = JOURNAL_APPEND_REQUIRED_PAYLOAD_FIELDS.issubset(set(append_payload))
    learning_journal_status = _as_string(learning_journal.get("status"))
    append_happened = (
        append_count > 0
        or bool(written_entry_ids)
        or learning_journal_status == "written"
    )

    return {
        "append_happened": append_happened,
        "append_count": append_count,
        "event_sequence": event_sequence,
        "sources": _ordered_unique([value for value in source_candidates if value]),
        "written_entry_ids": written_entry_ids,
        "task_id": _as_string(append_payload.get("task_id")) or _as_string(journal_entry.get("task_id")),
        "contract_id": _as_string(append_payload.get("contract_id")),
        "task_type": _as_string(journal_entry.get("task_type"))
        or _as_string(_mapping_get(append_payload, "lesson_entry.task_type")),
        "tags": lesson_tags,
        "lesson_preview": lesson_preview,
        "confidence_bands": _ordered_unique([_confidence_band(value) for value in confidence_values]),
        "archive_statuses": archive_statuses,
        "payload_fields_complete": payload_fields_complete,
        "forbidden_mirrored_fields": forbidden_mirrored_fields,
        "learning_journal_status": learning_journal_status,
        "last_timestamp": last_timestamp,
    }


def to_baseline_artifacts(bundle: EvaluationInputBundle | Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    normalized = _coerce_bundle(bundle)
    task_summary = normalized.task_contract_summary
    event_summary = normalized.event_trace_summary
    journal_summary = normalized.journal_append_summary

    event_sequence = list(event_summary.get("event_sequence", []))
    journal_sequence = list(journal_summary.get("event_sequence", []))
    journal_sources = list(journal_summary.get("sources", []))
    journal_tags = list(journal_summary.get("tags", []))
    journal_entry_id = (
        list(journal_summary.get("written_entry_ids", []))[0]
        if journal_summary.get("written_entry_ids")
        else "summary-journal-entry"
    )
    journal_task_type = _as_string(journal_summary.get("task_type")) or _as_string(task_summary.get("task_type"))
    journal_timestamp = _as_string(journal_summary.get("last_timestamp")) or "1970-01-01T00:00:00+00:00"
    confidence = _confidence_value_from_bands(list(journal_summary.get("confidence_bands", [])))

    return {
        "verification_report": _deep_copy_optional_mapping(normalized.verification_report) or {},
        "residual_followup": _deep_copy_optional_mapping(normalized.residual_followup) or {},
        "metrics_summary": _deep_copy_optional_mapping(normalized.metrics_summary) or {},
        "event_trace": {
            "dispatch_trace": [
                {"event_name": event_name}
                for event_name in event_sequence
            ],
            "execution_status": _as_string(event_summary.get("status_hint")) or "unknown",
        },
        "journal_append_trace": {
            "dispatch_trace": [
                {"event_name": event_name}
                for event_name in journal_sequence
            ],
            "payload": {
                "event_id": journal_entry_id,
                "timestamp": journal_timestamp,
                "task_id": _as_string(journal_summary.get("task_id")) or _as_string(task_summary.get("task_id")),
                "contract_id": _as_string(journal_summary.get("contract_id")) or _as_string(task_summary.get("contract_id")),
                "schema_version": "v0.3",
                "lesson_entry": {
                    "entry_id": journal_entry_id,
                    "task_id": _as_string(journal_summary.get("task_id")) or _as_string(task_summary.get("task_id")),
                    "task_type": journal_task_type,
                    "tags": journal_tags,
                    "lesson": _as_string(journal_summary.get("lesson_preview")) or "journal append summary",
                    "source": journal_sources[0] if journal_sources else "success",
                    "confidence": confidence,
                    "created_at": journal_timestamp,
                },
                "source": journal_sources[0] if journal_sources else "success",
            },
            "journal_entry": {
                "entry_id": journal_entry_id,
                "task_id": _as_string(journal_summary.get("task_id")) or _as_string(task_summary.get("task_id")),
                "task_type": journal_task_type,
                "tags": journal_tags,
                "lesson": _as_string(journal_summary.get("lesson_preview")) or "journal append summary",
                "source": journal_sources[0] if journal_sources else "success",
                "confidence": confidence,
                "created_at": journal_timestamp,
            },
            "learning_journal": {
                "status": _as_string(journal_summary.get("learning_journal_status")) or (
                    "written" if bool(journal_summary.get("append_happened")) else "not_written"
                ),
                "written_entry_id": journal_entry_id if journal_summary.get("append_happened") else None,
                "written_source": journal_sources[0] if journal_sources else None,
            },
        },
    }


def to_realm_evaluator_payload(
    bundle: EvaluationInputBundle | Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _coerce_bundle(bundle)
    metrics_summary = _deep_copy_optional_mapping(normalized.metrics_summary)
    if metrics_summary is not None:
        return metrics_summary
    return {
        "event_count": 0,
        "metric_count": 0,
        "metrics": {},
    }


def _coerce_bundle(bundle: EvaluationInputBundle | Mapping[str, Any]) -> EvaluationInputBundle:
    if isinstance(bundle, EvaluationInputBundle):
        return bundle
    if not isinstance(bundle, Mapping):
        raise TypeError("bundle must be an EvaluationInputBundle or mapping")

    task_contract_summary = bundle.get("task_contract_summary")
    if not isinstance(task_contract_summary, Mapping):
        raise TypeError("bundle.task_contract_summary must be a mapping")

    return EvaluationInputBundle(
        task_contract_summary=_deep_copy_mapping(task_contract_summary),
        block_selection_report=_normalize_block_selection_report(
            bundle.get("block_selection_report")
            if isinstance(bundle.get("block_selection_report"), Mapping)
            else None
        ),
        verification_report=_deep_copy_optional_mapping(bundle.get("verification_report")),
        residual_followup=_deep_copy_optional_mapping(bundle.get("residual_followup")),
        metrics_summary=_deep_copy_optional_mapping(bundle.get("metrics_summary")),
        event_trace_summary=_deep_copy_mapping(
            bundle.get("event_trace_summary")
            if isinstance(bundle.get("event_trace_summary"), Mapping)
            else summarize_event_trace(None)
        ),
        journal_append_summary=_deep_copy_mapping(
            bundle.get("journal_append_summary")
            if isinstance(bundle.get("journal_append_summary"), Mapping)
            else summarize_journal_append_trace(None)
        ),
    )


def _normalize_block_selection_report(
    report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if report is None:
        return {
            "included_blocks": [],
            "excluded_blocks": [],
            "block_order": [],
            "limits": {},
        }
    return _deep_copy_mapping(report)


def _extract_trace_entries(
    payload: Mapping[str, Any] | Sequence[Any] | None,
) -> list[dict[str, Any]]:
    if payload is None:
        return []

    normalized = _to_plain_data(payload)
    if isinstance(normalized, Mapping):
        for candidate_key in ("dispatch_trace", "events"):
            candidate = normalized.get(candidate_key)
            if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes, bytearray)):
                return [
                    dict(item)
                    for item in candidate
                    if isinstance(item, Mapping)
                ]
        if normalized.get("event_name"):
            return [dict(normalized)]
        return []

    if isinstance(normalized, Sequence) and not isinstance(normalized, (str, bytes, bytearray)):
        return [
            dict(item)
            for item in normalized
            if isinstance(item, Mapping)
        ]
    return []


def _find_forbidden_keys(value: object, *, prefix: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = str(key)
            qualified = f"{prefix}{normalized_key}" if prefix else normalized_key
            if normalized_key in FORBIDDEN_JOURNAL_TRACE_KEYS:
                found.add(qualified)
            found.update(_find_forbidden_keys(nested, prefix=f"{qualified}."))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            found.update(_find_forbidden_keys(nested, prefix=prefix))
    return found


def _mapping_get(mapping: Mapping[str, Any], path: str) -> object:
    current: object = mapping
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _to_plain_data(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            key: _to_plain_data(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, Mapping):
        return {
            str(key): _to_plain_data(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_to_plain_data(item) for item in value]
    return value


def _deep_copy_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _to_plain_data(mapping)
    if not isinstance(normalized, Mapping):
        raise TypeError("expected a mapping-like object")
    return dict(normalized)


def _deep_copy_optional_mapping(mapping: object) -> dict[str, Any] | None:
    if mapping is None:
        return None
    normalized = _to_plain_data(mapping)
    if not isinstance(normalized, Mapping):
        raise TypeError("expected a mapping-like object")
    return dict(normalized)


def _normalize_string_list(value: object, *, limit: int | None = None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        candidates = list(value)
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        item = _as_string(candidate)
        if not item or item in seen:
            continue
        normalized.append(item)
        seen.add(item)
        if limit is not None and len(normalized) >= limit:
            break
    return normalized


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        ordered.append(value)
        seen.add(value)
    return ordered


def _count_labels(values: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _trace_status_hint(*, error_count: int, event_count: int) -> str:
    if error_count > 0:
        return "error"
    if event_count > 0:
        return "success"
    return "not_emitted"


def _shorten_text(value: str, *, limit: int = 160) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _safe_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_band(value: float) -> str:
    if value >= 0.8:
        return "high"
    if value >= 0.6:
        return "medium"
    return "low"


def _confidence_value_from_bands(bands: Sequence[str]) -> float:
    if "high" in bands:
        return 0.85
    if "medium" in bands:
        return 0.65
    if "low" in bands:
        return 0.4
    return 0.5


def _as_string(value: object) -> str:
    return str(value).strip() if value is not None else ""
