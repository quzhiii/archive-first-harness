from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


TASK_CONTRACT_SCHEMA_VERSION = "v1"


class TaskType(str, Enum):
    QA = "qa"
    RESEARCH = "research"
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    CODING = "coding"
    EXECUTION = "execution"
    PLANNING = "planning"
    REVIEW = "review"


class WritePermissionLevel(str, Enum):
    READ = "read"
    QUERY = "query"
    PROPOSE = "propose"
    WRITE = "write"
    DESTRUCTIVE_WRITE = "destructive_write"


class BudgetLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _clean_string_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


@dataclass(slots=True)
class TaskContract:
    contract_id: str
    goal: str
    success_criteria: list[str]
    allowed_tools: list[str]
    stop_conditions: list[str]
    expected_artifacts: list[str]
    task_id: str | None = None
    task_type: TaskType = TaskType.GENERATION
    schema_version: str = TASK_CONTRACT_SCHEMA_VERSION
    write_permission_level: WritePermissionLevel = WritePermissionLevel.READ
    token_budget: BudgetLevel = BudgetLevel.LOW
    latency_budget: BudgetLevel = BudgetLevel.LOW
    retrieval_budget: BudgetLevel = BudgetLevel.LOW
    verification_budget: BudgetLevel = BudgetLevel.LOW
    escalation_budget: BudgetLevel = BudgetLevel.LOW
    uncertainty_level: RiskLevel = RiskLevel.MEDIUM
    residual_risk_level: RiskLevel = RiskLevel.MEDIUM
    escalation_threshold: list[str] = field(default_factory=list)
    escalation_policy: list[str] = field(default_factory=list)
    methodology_family: str = "general"
    failure_escalation_policy: list[str] = field(default_factory=list)
    workflow_profile_id: str = "default_general"

    def __post_init__(self) -> None:
        self.contract_id = self.contract_id.strip()
        self.task_id = self.task_id.strip() if self.task_id else f"task-{uuid4().hex}"
        self.goal = self.goal.strip()
        self.success_criteria = _clean_string_list(self.success_criteria)
        self.allowed_tools = _clean_string_list(self.allowed_tools)
        self.stop_conditions = _clean_string_list(self.stop_conditions)
        self.expected_artifacts = _clean_string_list(self.expected_artifacts)
        self.escalation_threshold = _clean_string_list(self.escalation_threshold)
        self.escalation_policy = _clean_string_list(self.escalation_policy)
        self.failure_escalation_policy = _clean_string_list(
            self.failure_escalation_policy
        )
        self.methodology_family = self.methodology_family.strip()
        self.workflow_profile_id = self.workflow_profile_id.strip()
        self.schema_version = self.schema_version.strip()

        if not self.contract_id:
            raise ValueError("contract_id must not be empty")
        if not self.task_id:
            raise ValueError("task_id must not be empty")
        if not self.goal:
            raise ValueError("goal must not be empty")
        if not self.schema_version:
            raise ValueError("schema_version must not be empty")
        if not self.success_criteria:
            raise ValueError("success_criteria must not be empty")
        if not self.allowed_tools:
            raise ValueError("allowed_tools must not be empty")
        if not self.stop_conditions:
            raise ValueError("stop_conditions must not be empty")
        if not self.expected_artifacts:
            raise ValueError("expected_artifacts must not be empty")
        if not self.methodology_family:
            raise ValueError("methodology_family must not be empty")
        if not self.workflow_profile_id:
            raise ValueError("workflow_profile_id must not be empty")


@dataclass(slots=True)
class GlobalState:
    operating_principles: list[str] = field(default_factory=list)
    hard_constraints: list[str] = field(default_factory=list)
    permission_defaults: list[str] = field(default_factory=list)
    preferred_tools: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.operating_principles = _clean_string_list(self.operating_principles)
        self.hard_constraints = _clean_string_list(self.hard_constraints)
        self.permission_defaults = _clean_string_list(self.permission_defaults)
        self.preferred_tools = _clean_string_list(self.preferred_tools)


@dataclass(slots=True)
class ProjectBlock:
    project_id: str
    project_name: str
    current_phase: str = ""
    goals: list[str] = field(default_factory=list)
    key_dependencies: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    background_facts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.project_id = self.project_id.strip()
        self.project_name = self.project_name.strip()
        self.current_phase = self.current_phase.strip()
        self.goals = _clean_string_list(self.goals)
        self.key_dependencies = _clean_string_list(self.key_dependencies)
        self.milestones = _clean_string_list(self.milestones)
        self.background_facts = _clean_string_list(self.background_facts)

        if not self.project_id:
            raise ValueError("project_id must not be empty")
        if not self.project_name:
            raise ValueError("project_name must not be empty")


@dataclass(slots=True)
class TaskBlock:
    task_id: str
    current_goal: str
    contract_id: str | None = None
    assumptions: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    known_risks: list[str] = field(default_factory=list)
    residual_risk: dict[str, object] | None = None
    followup_required: bool = False
    governance_required: bool = False

    def __post_init__(self) -> None:
        self.task_id = self.task_id.strip()
        self.current_goal = self.current_goal.strip()
        self.contract_id = self.contract_id.strip() if self.contract_id else None
        self.assumptions = _clean_string_list(self.assumptions)
        self.blockers = _clean_string_list(self.blockers)
        self.next_steps = _clean_string_list(self.next_steps)
        self.known_risks = _clean_string_list(self.known_risks)
        if self.residual_risk is not None:
            if not isinstance(self.residual_risk, dict):
                raise ValueError("residual_risk must be a dictionary when provided")
            self.residual_risk = dict(self.residual_risk)
        if not isinstance(self.followup_required, bool):
            raise ValueError("followup_required must be a boolean")
        if not isinstance(self.governance_required, bool):
            raise ValueError("governance_required must be a boolean")

        if not self.task_id:
            raise ValueError("task_id must not be empty")
        if not self.current_goal:
            raise ValueError("current_goal must not be empty")


@dataclass(slots=True)
class WorkingContext:
    task_contract: TaskContract
    selected_global_notes: list[str] = field(default_factory=list)
    selected_project_notes: list[str] = field(default_factory=list)
    selected_task_notes: list[str] = field(default_factory=list)
    active_skills: list[str] = field(default_factory=list)
    tool_signatures: list[str] = field(default_factory=list)
    retrieval_packets: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.selected_global_notes = _clean_string_list(self.selected_global_notes)
        self.selected_project_notes = _clean_string_list(self.selected_project_notes)
        self.selected_task_notes = _clean_string_list(self.selected_task_notes)
        self.active_skills = _clean_string_list(self.active_skills)
        self.tool_signatures = _clean_string_list(self.tool_signatures)
        self.retrieval_packets = _clean_string_list(self.retrieval_packets)

