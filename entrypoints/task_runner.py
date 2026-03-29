from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from entrypoints.settings import Settings
from harness.contracts.profile_input_adapter import (
    ProfileInputResolution,
    resolve_surface_workflow_profile,
)
from harness.context.context_engine import ContextEngine
from harness.governance.policy import GovernancePolicy
from harness.journal.learning_journal import LearningJournal
from harness.state.models import TaskBlock
from harness.state.state_manager import StateManager
from harness.tools.tool_discovery_service import ToolDiscoveryService
from planner.task_contract_builder import TaskContractBuilder
from runtime.executor import Executor
from runtime.methodology_router import MethodologyRouter
from runtime.model_router import ModelRouter
from runtime.orchestrator import Orchestrator
from runtime.verifier import Verifier


@dataclass(slots=True)
class SurfaceTaskRequest:
    task: str
    task_type: str | None = None
    workflow_profile_id: str | None = None
    workflow_profile: str | None = None
    mission_profile_id: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)
    success_criteria: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.task = str(self.task).strip()
        self.task_type = _normalize_optional_string(self.task_type)
        self.workflow_profile_id = _normalize_optional_string(self.workflow_profile_id)
        self.workflow_profile = _normalize_optional_string(self.workflow_profile)
        self.mission_profile_id = _normalize_optional_string(self.mission_profile_id)
        self.constraints = dict(self.constraints or {})
        self.success_criteria = _normalize_string_list(self.success_criteria)
        self.expected_artifacts = _normalize_string_list(self.expected_artifacts)

        if not self.task:
            raise ValueError("task must not be empty")

    def profile_payload(self) -> dict[str, object]:
        return {
            "workflow_profile_id": self.workflow_profile_id,
            "workflow_profile": self.workflow_profile,
            "mission_profile_id": self.mission_profile_id,
            "task_type": self.task_type,
        }


def run_task_request(
    request: SurfaceTaskRequest | Mapping[str, object],
    settings: Settings,
    *,
    executor: Executor | None = None,
    orchestrator: Orchestrator | None = None,
) -> dict[str, Any]:
    surface_request = _coerce_surface_task_request(request)
    profile_resolution = resolve_surface_workflow_profile(
        surface_request.profile_payload(),
        task_type=surface_request.task_type,
    )

    artifacts_dir = settings.artifacts_dir
    state_dir = artifacts_dir / "state"
    contracts_dir = artifacts_dir / "contracts"
    state_dir.mkdir(parents=True, exist_ok=True)
    contracts_dir.mkdir(parents=True, exist_ok=True)

    builder_constraints = _build_builder_constraints(
        surface_request,
        settings=settings,
        profile_resolution=profile_resolution,
    )
    task_contract = TaskContractBuilder().build(
        surface_request.task,
        constraints=builder_constraints,
    )
    _write_json(contracts_dir / "latest_contract.json", _to_json_value(task_contract))

    state_manager = StateManager(state_dir)
    state_manager.save_task_block(
        TaskBlock(
            task_id=task_contract.task_id,
            current_goal=task_contract.goal,
            contract_id=task_contract.contract_id,
            next_steps=["Execute the surface task request."],
        )
    )

    active_executor = executor or Executor()
    active_orchestrator = orchestrator or Orchestrator()
    result = active_orchestrator.run(
        task_contract,
        state_manager,
        ContextEngine(),
        None,
        ToolDiscoveryService(),
        active_executor,
        verifier=Verifier(),
        methodology_router=MethodologyRouter(),
        model_router=ModelRouter(),
        governance_policy=GovernancePolicy(),
        learning_journal=LearningJournal(artifacts_dir / "learning_journal.jsonl"),
    )

    output = dict(result)
    output["surface"] = {
        "workflow_profile_id": profile_resolution.workflow_profile_id,
        "profile_resolution": profile_resolution.as_dict(),
    }
    output.setdefault("telemetry", output.get("metrics_summary"))
    output.setdefault("evaluation", output.get("realm_evaluation"))
    return output



def _coerce_surface_task_request(
    request: SurfaceTaskRequest | Mapping[str, object],
) -> SurfaceTaskRequest:
    if isinstance(request, SurfaceTaskRequest):
        return request
    if not isinstance(request, Mapping):
        raise TypeError("request must be a SurfaceTaskRequest or mapping")

    constraints = request.get("constraints")
    if constraints is None:
        normalized_constraints: dict[str, Any] = {}
    elif isinstance(constraints, Mapping):
        normalized_constraints = dict(constraints)
    else:
        raise TypeError("request.constraints must be a mapping when provided")

    return SurfaceTaskRequest(
        task=_normalize_required_string(request.get("task")),
        task_type=_normalize_optional_string(request.get("task_type")),
        workflow_profile_id=_normalize_optional_string(request.get("workflow_profile_id")),
        workflow_profile=_normalize_optional_string(request.get("workflow_profile")),
        mission_profile_id=_normalize_optional_string(request.get("mission_profile_id")),
        constraints=normalized_constraints,
        success_criteria=_normalize_string_list(request.get("success_criteria")),
        expected_artifacts=_normalize_string_list(request.get("expected_artifacts")),
    )



def _build_builder_constraints(
    request: SurfaceTaskRequest,
    *,
    settings: Settings,
    profile_resolution: ProfileInputResolution,
) -> dict[str, Any]:
    constraints = dict(request.constraints)
    for field_name in ("workflow_profile_id", "workflow_profile", "mission_profile_id"):
        constraints.pop(field_name, None)

    effective_task_type = request.task_type or _normalize_optional_string(constraints.get("task_type"))
    if effective_task_type:
        constraints["task_type"] = effective_task_type

    if request.success_criteria:
        constraints["success_criteria"] = list(request.success_criteria)
    if request.expected_artifacts:
        constraints["expected_artifacts"] = list(request.expected_artifacts)

    constraints.setdefault("token_budget", settings.default_token_budget)
    constraints.setdefault("latency_budget", settings.default_latency_budget)
    constraints["workflow_profile_id"] = profile_resolution.workflow_profile_id
    return constraints



def _normalize_required_string(value: object | None) -> str:
    text = _normalize_optional_string(value)
    return text or ""



def _normalize_optional_string(value: object | None) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None



def _normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        candidates = list(value)
    else:
        raise TypeError("expected a string or sequence of strings")

    normalized: list[str] = []
    for candidate in candidates:
        text = str(candidate).strip()
        if text:
            normalized.append(text)
    return normalized



def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json_dumps(payload),
        encoding="utf-8",
    )



def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)



def _to_json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _to_json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    return value
