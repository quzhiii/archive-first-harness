from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from entrypoints._utils import extract_mapping, normalize_optional_string


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
    from entrypoints._archive_compare import _verification_warning_codes

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

    from entrypoints._archive_compare import _verification_warning_codes

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
