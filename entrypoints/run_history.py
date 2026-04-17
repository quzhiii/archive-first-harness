from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from entrypoints._utils import normalize_optional_string


@dataclass(frozen=True, slots=True)
class RunHistoryEntry:
    run_id: str
    created_at: str
    batch_name: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    stopped_early: bool
    output_dir: str
    written_files: list[dict[str, str]]
    exported_formats: list[str]
    tag: str | None = None
    notes: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_run_id(
    batch_name: str | None,
    *,
    created_at: datetime | None = None,
    unique_suffix: str | None = None,
) -> str:
    timestamp = _coerce_created_at(created_at)
    slug = _normalize_run_fragment(batch_name) or "batch"
    suffix = _normalize_run_fragment(unique_suffix) or uuid4().hex[:6]
    return f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{slug}_{suffix}"


def build_run_history_entry(
    batch_result: Mapping[str, Any],
    export_result: Mapping[str, Any],
    *,
    run_id: str | None = None,
    created_at: datetime | None = None,
    tag: str | None = None,
    notes: str | None = None,
) -> RunHistoryEntry:
    if not isinstance(batch_result, Mapping):
        raise TypeError("batch_result must be a mapping")
    if not isinstance(export_result, Mapping):
        raise TypeError("export_result must be a mapping")

    timestamp = _coerce_created_at(created_at)
    batch_name = normalize_optional_string(batch_result.get("batch_name")) or "batch"
    resolved_run_id = normalize_optional_string(run_id) or build_run_id(
        batch_name, created_at=timestamp
    )
    output_dir = normalize_optional_string(export_result.get("output_dir"))
    if not output_dir:
        raise ValueError("export_result.output_dir must not be empty")

    return RunHistoryEntry(
        run_id=resolved_run_id,
        created_at=_format_created_at(timestamp),
        batch_name=batch_name,
        total_tasks=int(batch_result.get("total_tasks", 0) or 0),
        completed_tasks=int(batch_result.get("completed_tasks", 0) or 0),
        failed_tasks=int(batch_result.get("failed_tasks", 0) or 0),
        stopped_early=bool(batch_result.get("stopped_early", False)),
        output_dir=output_dir,
        written_files=_coerce_written_files(export_result.get("written_files")),
        exported_formats=_coerce_exported_formats(
            export_result.get("exported_formats")
        ),
        tag=normalize_optional_string(tag),
        notes=normalize_optional_string(notes),
    )


def append_run_history_entry(
    batch_result: Mapping[str, Any],
    export_result: Mapping[str, Any],
    history_file: str | Path | None = None,
    *,
    run_id: str | None = None,
    created_at: datetime | None = None,
    tag: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    entry = build_run_history_entry(
        batch_result,
        export_result,
        run_id=run_id,
        created_at=created_at,
        tag=tag,
        notes=notes,
    )
    manifest_path = _resolve_history_file(history_file, export_result)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(entry.as_dict(), ensure_ascii=True, sort_keys=True) + "\n"
        )
    return {
        "history_file": str(manifest_path),
        "run_id": entry.run_id,
        "created_at": entry.created_at,
    }


def list_run_history(
    history_file: str | Path, *, limit: int | None = None
) -> list[dict[str, Any]]:
    manifest_path = Path(history_file)
    if not manifest_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, Mapping):
            entries.append(dict(payload))
    if limit is None:
        return entries
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if limit == 0:
        return []
    return entries[-limit:]


def _resolve_history_file(
    history_file: str | Path | None, export_result: Mapping[str, Any]
) -> Path:
    if history_file is not None:
        history_text = normalize_optional_string(history_file)
        if not history_text:
            raise ValueError("history_file must not be empty")
        return Path(history_text)
    output_dir = normalize_optional_string(export_result.get("output_dir"))
    if not output_dir:
        raise ValueError("history_file requires export_result.output_dir to be set")
    return Path(output_dir) / "run_history.jsonl"


def _coerce_written_files(value: object) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    written_files: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        path_value = normalize_optional_string(item.get("path"))
        format_value = normalize_optional_string(item.get("format"))
        if not path_value or not format_value:
            continue
        written_files.append({"format": format_value, "path": path_value})
    return written_files


def _coerce_exported_formats(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    formats: list[str] = []
    for item in value:
        text = normalize_optional_string(item)
        if text:
            formats.append(text)
    return formats


def _coerce_created_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_created_at(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_run_fragment(value: object | None) -> str | None:
    text = normalize_optional_string(value)
    if not text:
        return None
    characters: list[str] = []
    previous_was_separator = False
    for char in text.lower():
        if char.isalnum():
            characters.append(char)
            previous_was_separator = False
            continue
        if char in {"-", "_"}:
            characters.append(char)
            previous_was_separator = False
            continue
        if not previous_was_separator:
            characters.append("_")
            previous_was_separator = True
    normalized = "".join(characters).strip("_-")
    return normalized or None
