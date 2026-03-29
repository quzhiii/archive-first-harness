from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harness.contracts.workflow_profile import (
    BUILTIN_WORKFLOW_PROFILES,
    DEFAULT_WORKFLOW_PROFILE_ID,
    resolve_workflow_profile,
)


@dataclass(frozen=True, slots=True)
class ProfileInterpretation:
    workflow_profile_id: str
    profile_name: str
    intent_class: str
    comparison_focus: tuple[str, ...]
    evaluation_focus: tuple[str, ...]
    artifact_relevance_hint: str
    metadata_tags: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "workflow_profile_id": self.workflow_profile_id,
            "profile_name": self.profile_name,
            "intent_class": self.intent_class,
            "comparison_focus": list(self.comparison_focus),
            "evaluation_focus": list(self.evaluation_focus),
            "artifact_relevance_hint": self.artifact_relevance_hint,
            "metadata_tags": list(self.metadata_tags),
        }


def build_profile_interpretation(
    profile_id: str | None,
    *,
    task_type: str | None = None,
    artifact_type: str | None = None,
) -> ProfileInterpretation:
    normalized_profile_id = str(profile_id or "").strip().lower()
    if normalized_profile_id and normalized_profile_id not in BUILTIN_WORKFLOW_PROFILES:
        profile = resolve_workflow_profile(DEFAULT_WORKFLOW_PROFILE_ID)
    else:
        profile = resolve_workflow_profile(normalized_profile_id or None, task_type=task_type)
    normalized_artifact_type = str(artifact_type or "").strip().lower()
    focus = tuple(profile.evaluation_bias[:2])
    return ProfileInterpretation(
        workflow_profile_id=profile.profile_id,
        profile_name=profile.name,
        intent_class=profile.intent_class,
        comparison_focus=focus,
        evaluation_focus=focus,
        artifact_relevance_hint=_artifact_relevance_hint(
            intent_class=profile.intent_class,
            artifact_type=normalized_artifact_type,
        ),
        metadata_tags=(
            f"profile:{profile.profile_id}",
            f"intent:{profile.intent_class}",
            f"artifact:{normalized_artifact_type or 'unknown'}",
        ),
    )


def _artifact_relevance_hint(*, intent_class: str, artifact_type: str) -> str:
    if artifact_type == "":
        return "general"

    primary_by_intent = {
        "general": {"verification_report", "residual_followup"},
        "analysis": {"verification_report", "event_trace", "residual_followup"},
        "build": {"verification_report", "residual_followup", "metrics_summary"},
        "evaluation": {"metrics_summary", "event_trace", "verification_report"},
        "planning": {"verification_report", "residual_followup"},
    }
    if artifact_type in primary_by_intent.get(intent_class, set()):
        return "primary"
    if artifact_type == "journal_append_trace":
        return "supplemental"
    return "supporting"
