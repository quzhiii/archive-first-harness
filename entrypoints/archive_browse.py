from __future__ import annotations

from pathlib import Path

from entrypoints._utils import normalize_optional_string
from entrypoints._archive_reader import _load_archive_entries, _read_archive_record
from entrypoints._archive_filter import _filter_archive_entries, _find_archive_entry_by_run_id
from entrypoints._archive_compare import compare_run_archives  # noqa: F401
from entrypoints._archive_formatter import (
    format_archive_brief,  # noqa: F401
    build_summarize_payload,
)


def _build_filters(workflow_profile_id, task_type, formation_id, status, failure_class):
    return {
        "workflow_profile_id": normalize_optional_string(workflow_profile_id),
        "task_type": normalize_optional_string(task_type),
        "formation_id": normalize_optional_string(formation_id),
        "status": normalize_optional_string(status),
        "failure_class": normalize_optional_string(failure_class),
    }


def browse_run_archives(
    archive_root, *, limit=10, workflow_profile_id=None, task_type=None,
    formation_id=None, status=None, failure_class=None,
):
    if limit < 0:
        raise ValueError("limit must be non-negative")
    p = Path(archive_root)
    entries, source = _load_archive_entries(p)
    filtered = _filter_archive_entries(
        entries, workflow_profile_id=workflow_profile_id, task_type=task_type,
        formation_id=formation_id, status=status, failure_class=failure_class,
    )
    selected = filtered[-limit:] if limit else []
    return {
        "archive_root": str(p), "index_file": str(p / "index.jsonl"),
        "entry_count": len(selected), "limit": int(limit),
        "filters": _build_filters(workflow_profile_id, task_type, formation_id, status, failure_class),
        "entries": selected, "source": source,
    }


def summarize_run_archives(
    archive_root, *, workflow_profile_id=None, task_type=None,
    formation_id=None, status=None, failure_class=None,
):
    p = Path(archive_root)
    entries, source = _load_archive_entries(p)
    filtered = _filter_archive_entries(
        entries, workflow_profile_id=workflow_profile_id, task_type=task_type,
        formation_id=formation_id, status=status, failure_class=failure_class,
    )
    return build_summarize_payload(
        p, filtered,
        _build_filters(workflow_profile_id, task_type, formation_id, status, failure_class),
        source,
    )


def read_latest_run_archive(archive_root):
    p = Path(archive_root)
    entries, source = _load_archive_entries(p)
    if not entries:
        raise FileNotFoundError(f"no run archives available in {p}")
    latest = entries[-1]
    return {
        "archive_root": str(p), "index_file": str(p / "index.jsonl"),
        "latest_archive": latest,
        "archive": _read_archive_record(Path(latest["archive_dir"])),
        "source": source,
    }


def find_run_archive(archive_root, run_id):
    run_id_text = normalize_optional_string(run_id)
    if not run_id_text:
        raise ValueError("run_id must not be empty")
    p = Path(archive_root)
    entries, source = _load_archive_entries(p)
    entry = _find_archive_entry_by_run_id(entries, run_id_text)
    if entry is None:
        raise LookupError(f"run_id not found: {run_id_text}")
    return {
        "archive_root": str(p), "index_file": str(p / "index.jsonl"),
        "entry": entry,
        "archive": _read_archive_record(Path(entry["archive_dir"])),
        "source": source,
    }
