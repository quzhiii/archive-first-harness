from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from entrypoints._utils import (
    json_dumps,
    normalize_optional_string,
    normalize_required_string,
    normalize_string_list,
    to_json_value,
)
from entrypoints.run_archive import write_run_archive
from entrypoints.run_history import build_run_id
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
        self.task_type = normalize_optional_string(self.task_type)
        self.workflow_profile_id = normalize_optional_string(self.workflow_profile_id)
        self.workflow_profile = normalize_optional_string(self.workflow_profile)
        self.mission_profile_id = normalize_optional_string(self.mission_profile_id)
        self.constraints = dict(self.constraints or {})
        self.success_criteria = normalize_string_list(self.success_criteria)
        self.expected_artifacts = normalize_string_list(self.expected_artifacts)

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
    created_at = datetime.now(UTC)
    surface_request = _coerce_surface_task_request(request)
    profile_resolution = resolve_surface_workflow_profile(
        surface_request.profile_payload(),
        task_type=surface_request.task_type,
    )
    trace_events: list[dict[str, Any]] = [
        {
            "timestamp": _timestamp_now(),
            "event_type": "surface_request_received",
            "status": "ok",
            "metadata": {
                "task_type": surface_request.task_type or "",
            },
        }
    ]

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
    trace_events.append(
        {
            "timestamp": _timestamp_now(),
            "event_type": "task_contract_built",
            "status": "ok",
            "metadata": {
                "task_id": task_contract.task_id,
                "contract_id": task_contract.contract_id,
                "workflow_profile_id": task_contract.workflow_profile_id,
            },
        }
    )
    _write_json(contracts_dir / "latest_contract.json", to_json_value(task_contract))

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
    surface_payload = {
        "workflow_profile_id": profile_resolution.workflow_profile_id,
        "profile_resolution": profile_resolution.as_dict(),
    }
    archive_surface_payload = {
        "task": surface_request.task,
        "task_type": surface_request.task_type,
        **surface_payload,
    }
    output["surface"] = surface_payload
    output.setdefault("telemetry", output.get("metrics_summary"))
    output.setdefault("evaluation", output.get("realm_evaluation"))

    execution_result = output.get("execution_result")
    if isinstance(execution_result, Mapping):
        trace_events.append(
            {
                "timestamp": _timestamp_now(),
                "event_type": "runtime_completed",
                "status": str(execution_result.get("status") or "unknown"),
                "metadata": {
                    "tool_name": str(execution_result.get("tool_name") or ""),
                    "sandboxed": bool(
                        execution_result.get("metadata", {}).get("sandboxed")
                    )
                    if isinstance(execution_result.get("metadata"), Mapping)
                    else False,
                },
            }
        )
    verification_report = output.get("verification_report")
    if isinstance(verification_report, Mapping):
        trace_events.append(
            {
                "timestamp": _timestamp_now(),
                "event_type": "verification_completed",
                "status": "passed"
                if bool(verification_report.get("passed"))
                else "failed",
                "metadata": {
                    "verification_status": str(
                        verification_report.get("status") or "unknown"
                    ),
                },
            }
        )
    residual_followup = output.get("residual_followup")
    if isinstance(residual_followup, Mapping):
        governance = (
            residual_followup.get("governance")
            if isinstance(residual_followup.get("governance"), Mapping)
            else None
        )
        trace_events.append(
            {
                "timestamp": _timestamp_now(),
                "event_type": "governance_completed",
                "status": str(governance.get("status") or "clear")
                if isinstance(governance, Mapping)
                else "clear",
                "metadata": {
                    "governance_required": bool(
                        governance.get("requires_governance_override")
                    )
                    if isinstance(governance, Mapping)
                    else False,
                },
            }
        )
    realm_evaluation = output.get("realm_evaluation")
    if isinstance(realm_evaluation, Mapping):
        trace_events.append(
            {
                "timestamp": _timestamp_now(),
                "event_type": "evaluation_completed",
                "status": str(realm_evaluation.get("status") or "unknown"),
                "metadata": {
                    "requires_human_review": bool(
                        realm_evaluation.get("requires_human_review")
                    ),
                },
            }
        )

    run_id = build_run_id(surface_request.task, created_at=created_at)
    try:
        archive_result = write_run_archive(
            archive_root=artifacts_dir / "runs",
            run_id=run_id,
            created_at=created_at,
            surface_request=surface_payload,
            run_result=output,
            formation_id="default",
            policy_mode="default",
            trace_events=trace_events,
        )
    except Exception as exc:
        output["run_archive"] = {
            "status": "failed",
            "run_id": run_id,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
    else:
        output["run_archive"] = archive_result
    return output


def surface_result_succeeded(result: Mapping[str, Any]) -> bool:
    execution_result = result.get("execution_result")
    verification_report = result.get("verification_report")
    if not isinstance(execution_result, Mapping):
        return False
    if not isinstance(verification_report, Mapping):
        return False
    execution_ok = str(execution_result.get("status") or "") == "success"
    verification_ok = bool(verification_report.get("passed"))
    return execution_ok and verification_ok


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
        task=normalize_required_string(request.get("task")),
        task_type=normalize_optional_string(request.get("task_type")),
        workflow_profile_id=normalize_optional_string(
            request.get("workflow_profile_id")
        ),
        workflow_profile=normalize_optional_string(request.get("workflow_profile")),
        mission_profile_id=normalize_optional_string(request.get("mission_profile_id")),
        constraints=normalized_constraints,
        success_criteria=normalize_string_list(request.get("success_criteria")),
        expected_artifacts=normalize_string_list(request.get("expected_artifacts")),
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

    effective_task_type = request.task_type or normalize_optional_string(
        constraints.get("task_type")
    )
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


def _timestamp_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json_dumps(payload),
        encoding="utf-8",
    )
