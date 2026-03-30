from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from entrypoints.history_summary import build_run_history_summary, build_run_history_summary_entry
from entrypoints.run_history import list_run_history



def get_latest_run_id(
    history_file: str | Path,
    *,
    latest_run_file: str | Path | None = None,
) -> str:
    payload = read_latest_run(history_file, latest_run_file=latest_run_file)
    latest_run = _extract_entry(payload, "latest_run")
    run_id = _normalize_optional_string(latest_run.get("run_id"))
    if not run_id:
        raise ValueError("latest run entry is missing run_id")
    return run_id



def get_latest_run_output_dir(
    history_file: str | Path,
    *,
    latest_run_file: str | Path | None = None,
) -> str:
    payload = read_latest_run(history_file, latest_run_file=latest_run_file)
    latest_run = _extract_entry(payload, "latest_run")
    output_dir = _normalize_optional_string(latest_run.get("output_dir"))
    if not output_dir:
        raise ValueError("latest run entry is missing output_dir")
    return output_dir



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



def find_run_history_entry(
    history_file: str | Path,
    run_id: str,
    *,
    summary_file: str | Path | None = None,
) -> dict[str, Any]:
    run_id_text = _normalize_optional_string(run_id)
    if not run_id_text:
        raise ValueError("run_id must not be empty")

    history_path = Path(history_file)
    summary_payload: dict[str, Any] | None = None
    try:
        summary_payload = read_run_history_summary(
            history_path,
            summary_file=summary_file,
            limit=None,
        )
    except FileNotFoundError:
        summary_payload = None

    if summary_payload is not None:
        entry = _find_entry_by_run_id(summary_payload.get("entries"), run_id_text)
        if entry is not None:
            return {
                "history_file": str(summary_payload.get("history_file") or history_path),
                "entry": entry,
                "source": _normalize_optional_string(summary_payload.get("source")) or "unknown",
            }
        if summary_payload.get("source") == "manifest":
            raise LookupError(f"run_id not found: {run_id_text}")

    manifest_entries = list_run_history(history_path)
    if manifest_entries:
        for item in manifest_entries:
            if _normalize_optional_string(item.get("run_id")) == run_id_text:
                return {
                    "history_file": str(history_path),
                    "entry": build_run_history_summary_entry(item).as_dict(),
                    "source": "manifest",
                }
        raise LookupError(f"run_id not found: {run_id_text}")

    if summary_payload is not None:
        raise LookupError(f"run_id not found: {run_id_text}")
    raise FileNotFoundError(f"no run history entries available in {history_path}")



def format_history_brief(payload: Mapping[str, Any]) -> str:
    if "latest_run" in payload:
        return _format_entry_payload(
            title="Latest run",
            entry=_extract_entry(payload, "latest_run"),
            source=_normalize_optional_string(payload.get("source")) or "unknown",
            history_file=_normalize_optional_string(payload.get("history_file")) or "",
        )
    if "entry" in payload:
        return _format_entry_payload(
            title="History entry",
            entry=_extract_entry(payload, "entry"),
            source=_normalize_optional_string(payload.get("source")) or "unknown",
            history_file=_normalize_optional_string(payload.get("history_file")) or "",
        )
    if isinstance(payload.get("entries"), list):
        return _format_summary_payload(payload)
    raise ValueError("history payload is invalid")



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



def _find_entry_by_run_id(value: object, run_id: str) -> dict[str, Any] | None:
    for entry in _coerce_summary_entries(value):
        if _normalize_optional_string(entry.get("run_id")) == run_id:
            return entry
    return None



def _extract_entry(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    entry = payload.get(key)
    if not isinstance(entry, Mapping):
        raise ValueError(f"{key} payload is invalid")
    return dict(entry)



def _format_entry_payload(
    *,
    title: str,
    entry: Mapping[str, Any],
    source: str,
    history_file: str,
) -> str:
    return "\n".join(
        [
            title,
            f"source: {source}",
            f"history_file: {history_file}",
            f"run_id: {_normalize_optional_string(entry.get('run_id')) or ''}",
            f"created_at: {_normalize_optional_string(entry.get('created_at')) or ''}",
            f"batch_name: {_normalize_optional_string(entry.get('batch_name')) or ''}",
            "totals: "
            + f"total={int(entry.get('total_tasks', 0) or 0)} "
            + f"completed={int(entry.get('completed_tasks', 0) or 0)} "
            + f"failed={int(entry.get('failed_tasks', 0) or 0)} "
            + f"stopped_early={'yes' if bool(entry.get('stopped_early', False)) else 'no'}",
            f"formats: {_format_formats(entry.get('formats'))}",
            f"output_dir: {_normalize_optional_string(entry.get('output_dir')) or ''}",
        ]
    )



def _format_summary_payload(payload: Mapping[str, Any]) -> str:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("history summary payload is invalid")
    lines = [
        "History summary",
        f"source: {_normalize_optional_string(payload.get('source')) or 'unknown'}",
        f"history_file: {_normalize_optional_string(payload.get('history_file')) or ''}",
        f"entry_count: {int(payload.get('entry_count', 0) or 0)}",
        f"limit: {int(payload.get('limit', 0) or 0)}",
    ]
    if not entries:
        lines.append("entries: none")
        return "\n".join(lines)
    lines.append("entries:")
    for item in _coerce_summary_entries(entries):
        lines.append(
            "- "
            + f"{_normalize_optional_string(item.get('run_id')) or ''} | "
            + f"{_normalize_optional_string(item.get('created_at')) or ''} | "
            + f"batch={_normalize_optional_string(item.get('batch_name')) or ''} | "
            + f"total={int(item.get('total_tasks', 0) or 0)} | "
            + f"completed={int(item.get('completed_tasks', 0) or 0)} | "
            + f"failed={int(item.get('failed_tasks', 0) or 0)} | "
            + f"stopped_early={'yes' if bool(item.get('stopped_early', False)) else 'no'} | "
            + f"formats={_format_formats(item.get('formats'))} | "
            + f"output_dir={_normalize_optional_string(item.get('output_dir')) or ''}"
        )
    return "\n".join(lines)



def _format_formats(value: object) -> str:
    if not isinstance(value, list):
        return "none"
    items = [str(item).strip() for item in value if str(item).strip()]
    return ",".join(items) if items else "none"



def _normalize_optional_string(value: object | None) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None
