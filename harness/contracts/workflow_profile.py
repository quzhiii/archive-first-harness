from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from harness.state.models import TaskType


DEFAULT_WORKFLOW_PROFILE_ID = "default_general"


@dataclass(frozen=True, slots=True)
class WorkflowProfile:
    """Describe a small task-semantic profile without adding a control plane.

    The profile only carries stable semantic hints for contract summaries,
    context selection preference, and evaluator interpretation.
    It does not route execution, override governance, or create new runtime state.
    """

    profile_id: str
    name: str
    intent_class: str
    success_focus: tuple[str, ...]
    artifact_expectation: tuple[str, ...]
    context_bias: tuple[str, ...]
    evaluation_bias: tuple[str, ...]
    notes: str = ""

    def as_summary(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "intent_class": self.intent_class,
            "success_focus": list(self.success_focus),
        }


BUILTIN_WORKFLOW_PROFILES: dict[str, WorkflowProfile] = {
    DEFAULT_WORKFLOW_PROFILE_ID: WorkflowProfile(
        profile_id=DEFAULT_WORKFLOW_PROFILE_ID,
        name="Default General",
        intent_class="general",
        success_focus=("task completion", "scope discipline"),
        artifact_expectation=("requested artifact",),
        context_bias=("task_block", "task_contract"),
        evaluation_bias=("baseline stability",),
        notes="Fallback profile when no narrower task semantics are available.",
    ),
    "research_analysis": WorkflowProfile(
        profile_id="research_analysis",
        name="Research Analysis",
        intent_class="analysis",
        success_focus=("evidence quality", "scope discipline"),
        artifact_expectation=("report", "answer"),
        context_bias=("project_block", "distilled_summary", "journal_lessons_active"),
        evaluation_bias=("trace completeness", "verification clarity"),
        notes="Prefer evidence-bearing context and compact reusable lessons.",
    ),
    "implementation_build": WorkflowProfile(
        profile_id="implementation_build",
        name="Implementation Build",
        intent_class="build",
        success_focus=("artifact correctness", "execution safety"),
        artifact_expectation=("patch", "validated output"),
        context_bias=("task_block", "residual_state", "distilled_summary"),
        evaluation_bias=("verification clarity", "execution stability"),
        notes="Keep task-local execution context primary and residual signals visible.",
    ),
    "evaluation_regression": WorkflowProfile(
        profile_id="evaluation_regression",
        name="Evaluation Regression",
        intent_class="evaluation",
        success_focus=("drift visibility", "metrics stability"),
        artifact_expectation=("report", "diff"),
        context_bias=("distilled_summary", "task_block", "project_block"),
        evaluation_bias=("baseline drift", "metrics stability"),
        notes="Favor regression-facing summaries without turning compare into a gate.",
    ),
    "planning_design": WorkflowProfile(
        profile_id="planning_design",
        name="Planning Design",
        intent_class="planning",
        success_focus=("constraint coverage", "artifact completeness"),
        artifact_expectation=("plan", "design"),
        context_bias=("project_block", "distilled_summary", "task_block"),
        evaluation_bias=("contract completeness", "artifact fit"),
        notes="Favor higher-level project context while keeping task constraints explicit.",
    ),
}


TASK_TYPE_PROFILE_DEFAULTS = {
    TaskType.RESEARCH: "research_analysis",
    TaskType.RETRIEVAL: "research_analysis",
    TaskType.CODING: "implementation_build",
    TaskType.EXECUTION: "implementation_build",
    TaskType.QA: "evaluation_regression",
    TaskType.REVIEW: "evaluation_regression",
    TaskType.PLANNING: "planning_design",
    TaskType.GENERATION: DEFAULT_WORKFLOW_PROFILE_ID,
}

_PROFILE_DELIMITER_PATTERN = re.compile(r"[\s\-]+")
_PROFILE_UNDERSCORE_PATTERN = re.compile(r"_+")


def normalize_workflow_profile_id(value: object | None) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    normalized = _PROFILE_DELIMITER_PATTERN.sub("_", text)
    normalized = _PROFILE_UNDERSCORE_PATTERN.sub("_", normalized)
    return normalized.strip("_")


def is_known_workflow_profile_id(value: object | None) -> bool:
    return normalize_workflow_profile_id(value) in BUILTIN_WORKFLOW_PROFILES


def default_workflow_profile_id_for_task_type(task_type: TaskType | str | None) -> str:
    if task_type is None:
        return DEFAULT_WORKFLOW_PROFILE_ID
    if isinstance(task_type, TaskType):
        normalized = task_type
    else:
        try:
            normalized = TaskType(str(task_type).strip().lower())
        except ValueError:
            return DEFAULT_WORKFLOW_PROFILE_ID
    return TASK_TYPE_PROFILE_DEFAULTS.get(normalized, DEFAULT_WORKFLOW_PROFILE_ID)


def resolve_workflow_profile(
    profile_id: str | None,
    *,
    task_type: TaskType | str | None = None,
) -> WorkflowProfile:
    normalized = normalize_workflow_profile_id(profile_id)
    if normalized and normalized in BUILTIN_WORKFLOW_PROFILES:
        return BUILTIN_WORKFLOW_PROFILES[normalized]

    fallback_id = default_workflow_profile_id_for_task_type(task_type)
    return BUILTIN_WORKFLOW_PROFILES.get(fallback_id, BUILTIN_WORKFLOW_PROFILES[DEFAULT_WORKFLOW_PROFILE_ID])



