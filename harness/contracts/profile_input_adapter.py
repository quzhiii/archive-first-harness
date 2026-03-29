from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from harness.contracts.workflow_profile import (
    DEFAULT_WORKFLOW_PROFILE_ID,
    default_workflow_profile_id_for_task_type,
    is_known_workflow_profile_id,
    normalize_workflow_profile_id,
)
from harness.state.models import TaskType


PROFILE_INPUT_PRECEDENCE = (
    "workflow_profile_id",
    "workflow_profile",
    "mission_profile_id",
)


@dataclass(frozen=True, slots=True)
class ProfileInputResolution:
    workflow_profile_id: str
    source: str
    used_fallback: bool
    fallback_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "workflow_profile_id": self.workflow_profile_id,
            "source": self.source,
            "used_fallback": self.used_fallback,
            "fallback_reason": self.fallback_reason,
        }


def resolve_surface_workflow_profile(
    payload: Mapping[str, object] | None,
    *,
    task_type: TaskType | str | None = None,
) -> ProfileInputResolution:
    options = dict(payload or {})
    effective_task_type = task_type if task_type is not None else options.get("task_type")
    first_empty_field: str | None = None

    for field_name in PROFILE_INPUT_PRECEDENCE:
        raw_value = options.get(field_name)
        normalized_value = normalize_workflow_profile_id(raw_value)
        if normalized_value:
            if is_known_workflow_profile_id(normalized_value):
                return ProfileInputResolution(
                    workflow_profile_id=normalized_value,
                    source=field_name,
                    used_fallback=False,
                )
            return _build_fallback_resolution(
                effective_task_type,
                fallback_reason=f"{field_name}_unknown",
            )
        if field_name in options and first_empty_field is None:
            first_empty_field = field_name

    if first_empty_field is not None:
        return _build_fallback_resolution(
            effective_task_type,
            fallback_reason=f"{first_empty_field}_empty",
        )
    return _build_fallback_resolution(
        effective_task_type,
        fallback_reason="profile_not_provided",
    )


def _build_fallback_resolution(
    task_type: TaskType | str | None,
    *,
    fallback_reason: str,
) -> ProfileInputResolution:
    resolved_profile_id = default_workflow_profile_id_for_task_type(task_type)
    source = (
        DEFAULT_WORKFLOW_PROFILE_ID
        if resolved_profile_id == DEFAULT_WORKFLOW_PROFILE_ID
        else "task_type_default"
    )
    return ProfileInputResolution(
        workflow_profile_id=resolved_profile_id,
        source=source,
        used_fallback=True,
        fallback_reason=fallback_reason,
    )
