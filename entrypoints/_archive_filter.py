from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from entrypoints._utils import normalize_optional_string


def _filter_archive_entries(
    entries: list[dict[str, Any]],
    *,
    workflow_profile_id: str | None,
    task_type: str | None,
    formation_id: str | None,
    status: str | None,
    failure_class: str | None,
) -> list[dict[str, Any]]:
    workflow_profile_id_text = normalize_optional_string(workflow_profile_id)
    task_type_text = normalize_optional_string(task_type)
    formation_id_text = normalize_optional_string(formation_id)
    status_text = normalize_optional_string(status)
    failure_class_text = normalize_optional_string(failure_class)

    filtered: list[dict[str, Any]] = []
    for entry in entries:
        if (
            workflow_profile_id_text
            and normalize_optional_string(entry.get("workflow_profile_id"))
            != workflow_profile_id_text
        ):
            continue
        if (
            task_type_text
            and normalize_optional_string(entry.get("task_type")) != task_type_text
        ):
            continue
        if (
            formation_id_text
            and normalize_optional_string(entry.get("formation_id"))
            != formation_id_text
        ):
            continue
        if (
            status_text
            and normalize_optional_string(entry.get("status")) != status_text
        ):
            continue
        if (
            failure_class_text
            and normalize_optional_string(entry.get("failure_class"))
            != failure_class_text
        ):
            continue
        filtered.append(entry)
    return filtered


def _find_archive_entry_by_run_id(
    entries: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any] | None:
    for entry in entries:
        if normalize_optional_string(entry.get("run_id")) == run_id:
            return entry
    return None
