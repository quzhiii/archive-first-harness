from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import uuid4

from harness.contracts.profile_input_adapter import resolve_surface_workflow_profile
from harness.state.models import (
    BudgetLevel,
    RiskLevel,
    TASK_CONTRACT_SCHEMA_VERSION,
    TaskContract,
    TaskType,
    WritePermissionLevel,
)


DEFAULT_SUCCESS_CRITERIA = {
    TaskType.CODING: "Implement the requested code change without violating the stated constraints.",
    TaskType.PLANNING: "Produce a concrete plan that matches the stated task and constraints.",
    TaskType.REVIEW: "Provide a review outcome that clearly distinguishes findings from acceptable behavior.",
    TaskType.RESEARCH: "Produce a structured answer grounded in the available task description.",
    TaskType.RETRIEVAL: "Return the requested information relevant to the user task.",
    TaskType.QA: "Verify the requested behavior and report whether it satisfies the task.",
    TaskType.EXECUTION: "Complete the requested action within the allowed scope and report the result.",
    TaskType.GENERATION: "Produce an output that directly addresses the user task.",
}

DEFAULT_ARTIFACTS = {
    TaskType.CODING: ["code_patch"],
    TaskType.PLANNING: ["plan"],
    TaskType.REVIEW: ["audit_note"],
    TaskType.RESEARCH: ["report"],
    TaskType.RETRIEVAL: ["answer"],
    TaskType.QA: ["report"],
    TaskType.EXECUTION: ["report"],
    TaskType.GENERATION: ["answer"],
}

DEFAULT_ALLOWED_TOOLS = {
    TaskType.CODING: ["read_files", "edit_files", "run_tests"],
    TaskType.PLANNING: ["read_files", "draft"],
    TaskType.REVIEW: ["read_files", "inspect_artifacts"],
    TaskType.RESEARCH: ["read_files", "search_notes", "summarize"],
    TaskType.RETRIEVAL: ["search", "read_files"],
    TaskType.QA: ["read_files", "run_tests"],
    TaskType.EXECUTION: ["read_files", "run_command"],
    TaskType.GENERATION: ["search"],
}

DEFAULT_BUDGETS = {
    TaskType.CODING: {
        "token_budget": BudgetLevel.MEDIUM,
        "latency_budget": BudgetLevel.MEDIUM,
        "retrieval_budget": BudgetLevel.LOW,
        "verification_budget": BudgetLevel.MEDIUM,
        "escalation_budget": BudgetLevel.LOW,
    },
    TaskType.PLANNING: {
        "token_budget": BudgetLevel.MEDIUM,
        "latency_budget": BudgetLevel.MEDIUM,
        "retrieval_budget": BudgetLevel.LOW,
        "verification_budget": BudgetLevel.LOW,
        "escalation_budget": BudgetLevel.LOW,
    },
    TaskType.REVIEW: {
        "token_budget": BudgetLevel.MEDIUM,
        "latency_budget": BudgetLevel.MEDIUM,
        "retrieval_budget": BudgetLevel.LOW,
        "verification_budget": BudgetLevel.MEDIUM,
        "escalation_budget": BudgetLevel.LOW,
    },
    TaskType.RESEARCH: {
        "token_budget": BudgetLevel.MEDIUM,
        "latency_budget": BudgetLevel.MEDIUM,
        "retrieval_budget": BudgetLevel.MEDIUM,
        "verification_budget": BudgetLevel.LOW,
        "escalation_budget": BudgetLevel.LOW,
    },
    TaskType.RETRIEVAL: {
        "token_budget": BudgetLevel.LOW,
        "latency_budget": BudgetLevel.LOW,
        "retrieval_budget": BudgetLevel.MEDIUM,
        "verification_budget": BudgetLevel.LOW,
        "escalation_budget": BudgetLevel.LOW,
    },
    TaskType.QA: {
        "token_budget": BudgetLevel.MEDIUM,
        "latency_budget": BudgetLevel.MEDIUM,
        "retrieval_budget": BudgetLevel.LOW,
        "verification_budget": BudgetLevel.HIGH,
        "escalation_budget": BudgetLevel.LOW,
    },
    TaskType.EXECUTION: {
        "token_budget": BudgetLevel.LOW,
        "latency_budget": BudgetLevel.MEDIUM,
        "retrieval_budget": BudgetLevel.LOW,
        "verification_budget": BudgetLevel.MEDIUM,
        "escalation_budget": BudgetLevel.LOW,
    },
    TaskType.GENERATION: {
        "token_budget": BudgetLevel.LOW,
        "latency_budget": BudgetLevel.LOW,
        "retrieval_budget": BudgetLevel.LOW,
        "verification_budget": BudgetLevel.LOW,
        "escalation_budget": BudgetLevel.LOW,
    },
}

DEFAULT_METHOD_FAMILY = {
    TaskType.CODING: "build",
    TaskType.PLANNING: "architecture",
    TaskType.REVIEW: "compliance",
    TaskType.RESEARCH: "research",
    TaskType.RETRIEVAL: "research",
    TaskType.QA: "compliance",
    TaskType.EXECUTION: "build",
    TaskType.GENERATION: "writing",
}

TASK_TYPE_KEYWORDS = (
    (TaskType.REVIEW, ("review", "audit", "inspect", "code review")),
    (TaskType.PLANNING, ("plan", "roadmap", "design", "spec")),
    (TaskType.RESEARCH, ("research", "investigate", "analyze", "compare", "study")),
    (TaskType.RETRIEVAL, ("find", "lookup", "look up", "search", "fetch")),
    (TaskType.QA, ("qa", "smoke test", "verify behavior", "test flow")),
    (
        TaskType.CODING,
        ("code", "implement", "fix", "bug", "refactor", "patch", "function", "module"),
    ),
    (TaskType.EXECUTION, ("run", "execute", "invoke", "deploy")),
)


def _normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        item = value.strip()
        return [item] if item else []
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        normalized: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized
    raise TypeError("expected a string or a sequence of strings")


class TaskContractBuilder:
    """Build a minimal TaskContract from a user task and optional overrides."""

    schema_version = TASK_CONTRACT_SCHEMA_VERSION

    def build(
        self,
        user_task: str,
        constraints: Mapping[str, object] | None = None,
    ) -> TaskContract:
        goal = user_task.strip()
        if not goal:
            raise ValueError("user_task must not be empty")

        options = dict(constraints or {})
        task_type = self._resolve_task_type(goal, options.get("task_type"))
        budgets = self._resolve_budgets(task_type, options)

        return TaskContract(
            task_id=self._resolve_task_id(options),
            contract_id=self._new_contract_id(),
            schema_version=self.schema_version,
            task_type=task_type,
            goal=goal,
            success_criteria=self._resolve_success_criteria(goal, task_type, options),
            expected_artifacts=self._resolve_expected_artifacts(task_type, options),
            allowed_tools=self._resolve_allowed_tools(task_type, options),
            write_permission_level=self._resolve_write_permission(goal, task_type, options),
            token_budget=budgets["token_budget"],
            latency_budget=budgets["latency_budget"],
            retrieval_budget=budgets["retrieval_budget"],
            verification_budget=budgets["verification_budget"],
            escalation_budget=budgets["escalation_budget"],
            uncertainty_level=self._resolve_uncertainty(goal, task_type, options),
            residual_risk_level=self._resolve_residual_risk(goal, task_type, options),
            escalation_threshold=self._resolve_escalation_threshold(task_type, options),
            escalation_policy=self._resolve_escalation_policy(task_type, options),
            methodology_family=self._resolve_methodology_family(task_type, options),
            failure_escalation_policy=self._resolve_failure_policy(task_type, options),
            workflow_profile_id=self._resolve_workflow_profile_id(task_type, options),
            stop_conditions=self._resolve_stop_conditions(task_type, options),
        )

    def build_from_interview(
        self,
        user_task: str,
        interview_result: Mapping[str, object] | None,
        constraints: Mapping[str, object] | None = None,
    ) -> TaskContract:
        merged_constraints: dict[str, object] = {}
        if interview_result:
            clarified_constraints = interview_result.get("clarified_constraints", {})
            if isinstance(clarified_constraints, Mapping):
                merged_constraints.update(dict(clarified_constraints))
        if constraints:
            merged_constraints.update(dict(constraints))
        return self.build(user_task, constraints=merged_constraints)

    def _new_task_id(self) -> str:
        return f"task-{uuid4().hex}"

    def _new_contract_id(self) -> str:
        return f"contract-{uuid4().hex}"

    def _resolve_task_id(self, options: Mapping[str, object]) -> str:
        provided = str(options.get("task_id") or "").strip()
        return provided or self._new_task_id()

    def _resolve_task_type(
        self,
        user_task: str,
        override: object,
    ) -> TaskType:
        if override:
            return TaskType(str(override).strip().lower())

        lowered = user_task.lower()
        if any(keyword in lowered for keyword in ("implement", "fix", "refactor", "patch", "write code")):
            return TaskType.CODING

        matches: list[tuple[int, TaskType]] = []
        for task_type, keywords in TASK_TYPE_KEYWORDS:
            score = sum(1 for keyword in keywords if keyword in lowered)
            if score:
                matches.append((score, task_type))

        if matches:
            matches.sort(key=lambda item: item[0], reverse=True)
            return matches[0][1]
        return TaskType.GENERATION

    def _resolve_success_criteria(
        self,
        user_task: str,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> list[str]:
        provided = _normalize_string_list(options.get("success_criteria"))
        if provided:
            return provided

        summary = user_task.strip().rstrip(".")
        return [
            DEFAULT_SUCCESS_CRITERIA[task_type],
            f"Stay within the stated scope of: {summary}.",
        ]

    def _resolve_expected_artifacts(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> list[str]:
        provided = _normalize_string_list(options.get("expected_artifacts"))
        return provided or list(DEFAULT_ARTIFACTS[task_type])

    def _resolve_allowed_tools(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> list[str]:
        provided = _normalize_string_list(options.get("allowed_tools"))
        return provided or list(DEFAULT_ALLOWED_TOOLS[task_type])

    def _resolve_write_permission(
        self,
        user_task: str,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> WritePermissionLevel:
        if options.get("write_permission_level"):
            return WritePermissionLevel(str(options["write_permission_level"]).strip().lower())

        lowered = user_task.lower()
        destructive_keywords = ("delete", "drop", "destroy", "reset", "remove permanently")
        write_keywords = ("implement", "fix", "edit", "update", "write", "patch", "create")

        if any(keyword in lowered for keyword in destructive_keywords):
            return WritePermissionLevel.DESTRUCTIVE_WRITE
        if task_type == TaskType.CODING or any(keyword in lowered for keyword in write_keywords):
            return WritePermissionLevel.WRITE
        if task_type in {TaskType.PLANNING, TaskType.GENERATION}:
            return WritePermissionLevel.PROPOSE
        if task_type == TaskType.RETRIEVAL:
            return WritePermissionLevel.QUERY
        return WritePermissionLevel.READ

    def _resolve_budgets(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> dict[str, BudgetLevel]:
        budgets = dict(DEFAULT_BUDGETS[task_type])
        for field_name in (
            "token_budget",
            "latency_budget",
            "retrieval_budget",
            "verification_budget",
            "escalation_budget",
        ):
            value = options.get(field_name)
            if value:
                budgets[field_name] = BudgetLevel(str(value).strip().lower())
        return budgets

    def _resolve_uncertainty(
        self,
        user_task: str,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> RiskLevel:
        if options.get("uncertainty_level"):
            return RiskLevel(str(options["uncertainty_level"]).strip().lower())

        if task_type == TaskType.RETRIEVAL:
            return RiskLevel.LOW
        if any(token in user_task.lower() for token in ("unclear", "ambiguous", "unknown")):
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM

    def _resolve_residual_risk(
        self,
        user_task: str,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> RiskLevel:
        if options.get("residual_risk_level"):
            return RiskLevel(str(options["residual_risk_level"]).strip().lower())

        lowered = user_task.lower()
        if any(token in lowered for token in ("delete", "drop", "production", "migrate")):
            return RiskLevel.HIGH
        if task_type in {TaskType.RETRIEVAL, TaskType.GENERATION}:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    def _resolve_escalation_threshold(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> list[str]:
        provided = _normalize_string_list(options.get("escalation_threshold"))
        if provided:
            return provided
        return [
            "success criteria cannot be checked with the available information",
            "the requested action exceeds the current permission or budget",
        ]

    def _resolve_escalation_policy(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> list[str]:
        provided = _normalize_string_list(options.get("escalation_policy"))
        if provided:
            return provided
        return [
            "pause and request clarification",
            "narrow the task to the smallest verifiable scope",
        ]

    def _resolve_methodology_family(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> str:
        provided = str(options.get("methodology_family", "")).strip()
        return provided or DEFAULT_METHOD_FAMILY[task_type]

    def _resolve_failure_policy(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> list[str]:
        provided = _normalize_string_list(options.get("failure_escalation_policy"))
        if provided:
            return provided
        return [
            "do not repeat the same failing path without changing inputs or method",
            "fall back to clarification before widening scope",
        ]

    def _resolve_workflow_profile_id(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> str:
        resolution = resolve_surface_workflow_profile(options, task_type=task_type)
        return resolution.workflow_profile_id

    def _resolve_stop_conditions(
        self,
        task_type: TaskType,
        options: Mapping[str, object],
    ) -> list[str]:
        provided = _normalize_string_list(options.get("stop_conditions"))
        if provided:
            return provided
        return [
            "the task remains too ambiguous to verify",
            "the required action exceeds the allowed permission level",
            "the available budget is exhausted before the result can be validated",
        ]


