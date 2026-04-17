from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from entrypoints._utils import normalize_optional_string
from entrypoints.run_history import list_run_history


@dataclass(frozen=True, slots=True)
class RunHistorySummaryEntry:
    run_id: str
    created_at: str
    batch_name: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    stopped_early: bool
    output_dir: str
    formats: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_run_history_summary_entry(entry: Mapping[str, Any]) -> RunHistorySummaryEntry:
    if not isinstance(entry, Mapping):
        raise TypeError("entry must be a mapping")
    return RunHistorySummaryEntry(
        run_id=normalize_optional_string(entry.get("run_id")) or "",
        created_at=normalize_optional_string(entry.get("created_at")) or "",
        batch_name=normalize_optional_string(entry.get("batch_name")) or "batch",
        total_tasks=int(entry.get("total_tasks", 0) or 0),
        completed_tasks=int(entry.get("completed_tasks", 0) or 0),
        failed_tasks=int(entry.get("failed_tasks", 0) or 0),
        stopped_early=bool(entry.get("stopped_early", False)),
        output_dir=normalize_optional_string(entry.get("output_dir")) or "",
        formats=_coerce_formats(entry.get("exported_formats")),
    )


def build_run_history_summary(
    entries: Sequence[Mapping[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")
    selected_entries = list(entries)
    if limit is not None:
        if limit == 0:
            selected_entries = []
        else:
            selected_entries = selected_entries[-limit:]
    return [
        build_run_history_summary_entry(entry).as_dict() for entry in selected_entries
    ]


def write_latest_run_pointer(
    history_file: str | Path,
    latest_run_file: str | Path | None = None,
) -> dict[str, Any]:
    history_path = Path(history_file)
    entries = list_run_history(history_path)
    if not entries:
        raise ValueError("no run history entries available")

    latest_entry = build_run_history_summary_entry(entries[-1]).as_dict()
    pointer_path = _resolve_latest_run_file(latest_run_file, history_path)
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(
        json.dumps(
            {
                "history_file": str(history_path),
                "latest_run": latest_entry,
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return {
        "latest_run_file": str(pointer_path),
        "run_id": latest_entry["run_id"],
    }


def write_run_history_summary(
    history_file: str | Path,
    summary_file: str | Path | None = None,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    history_path = Path(history_file)
    summary_entries = build_run_history_summary(
        list_run_history(history_path), limit=limit
    )
    summary_path = _resolve_history_summary_file(summary_file, history_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "history_file": str(history_path),
                "entry_count": len(summary_entries),
                "limit": limit,
                "entries": summary_entries,
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return {
        "summary_file": str(summary_path),
        "entry_count": len(summary_entries),
        "limit": limit,
    }


def _resolve_latest_run_file(
    latest_run_file: str | Path | None,
    history_path: Path,
) -> Path:
    if latest_run_file is not None:
        path_text = normalize_optional_string(latest_run_file)
        if not path_text:
            raise ValueError("latest_run_file must not be empty")
        return Path(path_text)
    return history_path.parent / "latest_run.json"


def _resolve_history_summary_file(
    summary_file: str | Path | None,
    history_path: Path,
) -> Path:
    if summary_file is not None:
        path_text = normalize_optional_string(summary_file)
        if not path_text:
            raise ValueError("summary_file must not be empty")
        return Path(path_text)
    return history_path.parent / "run_history_summary.json"


def _coerce_formats(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    formats: list[str] = []
    for item in value:
        text = normalize_optional_string(item)
        if text:
            formats.append(text)
    return formats
