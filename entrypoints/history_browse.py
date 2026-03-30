from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from entrypoints.history_summary import build_run_history_summary, build_run_history_summary_entry
from entrypoints.run_history import list_run_history



def read_latest_run(
    history_file: str | Path,
    *,
    latest_run_file: str | Path | None = None,
) -> dict[str, Any]:
    history_path = Path(history_file)
    latest_path = _resolve_latest_run_file(latest_run_file, history_path)
    if latest_path.exists():
        payload = _read_json_mapping(latest_path)
        latest_run = payload.get("latest_run")
        if not isinstance(latest_run, Mapping):
            raise ValueError("latest run file is invalid")
        return {
            "history_file": str(payload.get("history_file") or history_path),
            "latest_run": dict(latest_run),
            "source": "latest_run_file",
        }

    manifest_entries = list_run_history(history_path, limit=1)
    if not manifest_entries:
        raise FileNotFoundError(f"no run history entries available in {history_path}")
    return {
        "history_file": str(history_path),
        "latest_run": build_run_history_summary_entry(manifest_entries[-1]).as_dict(),
        "source": "manifest",
    }



def read_run_history_summary(
    history_file: str | Path,
    *,
    summary_file: str | Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")

    history_path = Path(history_file)
    summary_path = _resolve_history_summary_file(summary_file, history_path)
    summary_payload: dict[str, Any] | None = None
    if summary_path.exists():
        payload = _read_json_mapping(summary_path)
        summary_entries = _coerce_summary_entries(payload.get("entries"))
        selected_entries = summary_entries if limit is None else summary_entries[-limit:]
        resolved_limit = int(payload.get("limit", len(selected_entries)) or 0)
        if limit is not None:
            resolved_limit = limit
        summary_payload = {
            "history_file": str(payload.get("history_file") or history_path),
            "entry_count": len(selected_entries),
            "limit": resolved_limit,
            "entries": selected_entries,
            "source": "summary_file",
        }
        if limit is None or limit <= len(summary_entries):
            return summary_payload

    manifest_entries = list_run_history(history_path)
    if manifest_entries:
        summary_entries = build_run_history_summary(manifest_entries, limit=limit)
        return {
            "history_file": str(history_path),
            "entry_count": len(summary_entries),
            "limit": len(summary_entries) if limit is None else limit,
            "entries": summary_entries,
            "source": "manifest",
        }
    if summary_payload is not None:
        return summary_payload
    if limit == 0:
        return {
            "history_file": str(history_path),
            "entry_count": 0,
            "limit": 0,
            "entries": [],
            "source": "manifest",
        }
    raise FileNotFoundError(f"no run history entries available in {history_path}")



def browse_run_history(
    history_file: str | Path,
    *,
    summary_file: str | Path | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    return read_run_history_summary(
        history_file,
        summary_file=summary_file,
        limit=limit,
    )



def _resolve_latest_run_file(
    latest_run_file: str | Path | None,
    history_path: Path,
) -> Path:
    if latest_run_file is not None:
        path_text = _normalize_optional_string(latest_run_file)
        if not path_text:
            raise ValueError("latest_run_file must not be empty")
        return Path(path_text)
    return history_path.parent / "latest_run.json"



def _resolve_history_summary_file(
    summary_file: str | Path | None,
    history_path: Path,
) -> Path:
    if summary_file is not None:
        path_text = _normalize_optional_string(summary_file)
        if not path_text:
            raise ValueError("summary_file must not be empty")
        return Path(path_text)
    return history_path.parent / "run_history_summary.json"



def _read_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return dict(payload)



def _coerce_summary_entries(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    entries: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            entries.append(dict(item))
    return entries



def _normalize_optional_string(value: object | None) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None
