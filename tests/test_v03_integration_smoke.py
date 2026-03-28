from __future__ import annotations

import unittest
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from harness.context.context_engine import ContextEngine
from harness.evaluation.realm_evaluator import RealmEvaluator
from harness.governance.policy import GovernancePolicy
from harness.hooks.hook_orchestrator import HookOrchestrator
from harness.journal.learning_journal import LearningJournal
from harness.sandbox.rollback import RollbackManager
from harness.sandbox.sandbox_executor import SandboxExecutor
from harness.state.models import BudgetLevel, RiskLevel, TaskBlock, TaskContract, TaskType, WritePermissionLevel
from harness.state.state_manager import StateManager
from harness.telemetry.metrics import MetricsAggregator
from harness.telemetry.tracer import Tracer
from harness.tools.tool_discovery_service import ToolDiscoveryService
from runtime.executor import Executor
from runtime.methodology_router import MethodologyRouter
from runtime.model_router import ModelRouter
from runtime.orchestrator import Orchestrator
from runtime.verifier import Verifier


class FailingExecutor:
    def execute_step(self, step, available_tools, working_context):
        return {
            "status": "error",
            "tool_name": step.get("tool_name"),
            "output": None,
            "error": {
                "type": "execution_error",
                "message": "forced failure for v0.3 integration smoke",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


def make_contract(
    *,
    task_id: str,
    contract_id: str,
    task_type: TaskType,
    write_permission_level: WritePermissionLevel,
    residual_risk_level: RiskLevel,
    allowed_tools: list[str],
    methodology_family: str,
    failure_escalation_policy: list[str] | None = None,
) -> TaskContract:
    return TaskContract(
        task_id=task_id,
        contract_id=contract_id,
        goal=f"Run {task_id} integration flow",
        success_criteria=["Produce a structured result."],
        allowed_tools=allowed_tools,
        stop_conditions=["Stop when the result is invalid."],
        expected_artifacts=["answer"],
        task_type=task_type,
        write_permission_level=write_permission_level,
        token_budget=BudgetLevel.LOW,
        latency_budget=BudgetLevel.LOW,
        uncertainty_level=RiskLevel.LOW,
        residual_risk_level=residual_risk_level,
        methodology_family=methodology_family,
        failure_escalation_policy=failure_escalation_policy or [],
    )


def run_v03_flow(
    *,
    base_dir: Path,
    contract: TaskContract,
    executor,
) -> dict[str, object]:
    state_manager = StateManager(base_dir / "state")
    state_manager.save_task_block(
        TaskBlock(
            task_id=contract.task_id,
            current_goal=contract.goal,
            contract_id=contract.contract_id,
            next_steps=["Run the v0.3 integrated path."],
        )
    )

    hooks = HookOrchestrator()
    tracer = Tracer()
    metrics = MetricsAggregator()
    evaluator = RealmEvaluator()
    rollback_manager = RollbackManager()
    sandbox_executor = SandboxExecutor(rollback_manager)
    journal = LearningJournal(base_dir / "learning_journal.jsonl")

    tracer.record_event(
        "run_started",
        {"task_id": contract.task_id, "contract_id": contract.contract_id},
    )

    orchestrator_result = Orchestrator().run(
        contract,
        state_manager,
        ContextEngine(),
        None,
        ToolDiscoveryService(),
        executor,
        verifier=Verifier(),
        methodology_router=MethodologyRouter(),
        model_router=ModelRouter(),
        governance_policy=GovernancePolicy(),
        learning_journal=journal,
        hook_orchestrator=hooks,
        sandbox_executor=sandbox_executor,
        rollback_manager=rollback_manager,
    )

    dispatch_trace = hooks.get_recent_dispatches()
    tracer.record_event(
        "run_finished",
        {
            "task_id": contract.task_id,
            "execution_status": orchestrator_result["execution_result"]["status"],
            "sandbox_triggered": orchestrator_result["sandbox_triggered"],
            "dispatch_count": len(dispatch_trace),
        },
    )

    working_context_summary = orchestrator_result["working_context_summary"]
    tracer.record_metric("token_count", 0)
    tracer.record_metric("latency_ms", 0)
    tracer.record_metric("retry_count", 0)
    tracer.record_metric(
        "rollback_count",
        1 if orchestrator_result["rollback_result"]["status"] == "rolled_back" else 0,
    )
    tracer.record_metric("tool_misuse_count", 0)
    tracer.record_metric(
        "execution_failure_count",
        1 if orchestrator_result["execution_result"]["status"] != "success" else 0,
    )
    tracer.record_metric(
        "context_size",
        working_context_summary["task_note_count"]
        + working_context_summary["project_note_count"]
        + working_context_summary["global_note_count"],
    )
    if orchestrator_result["selected_skills"]:
        tracer.record_metric("skill_hit_rate", 1)
    tracer.record_metric("human_handoff_count", 0)

    metrics_summary = metrics.aggregate(tracer.get_trace())
    evaluation = evaluator.evaluate(metrics_summary)
    lessons = journal.read_relevant_lessons(limit=10)

    return {
        "orchestrator_result": orchestrator_result,
        "dispatch_trace": dispatch_trace,
        "metrics_summary": metrics_summary,
        "evaluation": evaluation,
        "journal_entries": lessons,
    }


class V03IntegrationSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_v03_integration_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))

    def test_scenario_a_low_risk_success_path(self) -> None:
        result = run_v03_flow(
            base_dir=self.temp_dir / "scenario_a",
            contract=make_contract(
                task_id="task-v03-a",
                contract_id="contract-v03-a",
                task_type=TaskType.RETRIEVAL,
                write_permission_level=WritePermissionLevel.READ,
                residual_risk_level=RiskLevel.LOW,
                allowed_tools=["search", "read_files"],
                methodology_family="research",
            ),
            executor=Executor(),
        )

        orchestrator_result = result["orchestrator_result"]
        entry = result["journal_entries"][0]
        event_names = [event["event_name"] for event in result["dispatch_trace"]]
        journal_dispatch = next(
            event for event in result["dispatch_trace"] if event["event_name"] == "on_journal_append"
        )

        self.assertFalse(orchestrator_result["sandbox_triggered"])
        self.assertEqual(orchestrator_result["execution_result"]["status"], "success")
        self.assertEqual(orchestrator_result["verification_report"]["status"], "passed")
        self.assertEqual(orchestrator_result["residual_followup"]["reassessment"]["reassessed_level"], "low")
        self.assertIsNone(orchestrator_result["residual_followup"]["methodology_suggestion"])
        self.assertIsNone(orchestrator_result["residual_followup"]["model_suggestion"])
        self.assertEqual(entry["source"], "success")
        self.assertIn("on_verification_report", event_names)
        self.assertIn("on_journal_append", event_names)
        self.assertGreaterEqual(journal_dispatch["handler_count"], 1)
        self.assertEqual(result["evaluation"]["recommendation"], "keep")

    def test_scenario_b_sandbox_success_path(self) -> None:
        result = run_v03_flow(
            base_dir=self.temp_dir / "scenario_b",
            contract=make_contract(
                task_id="task-v03-b",
                contract_id="contract-v03-b",
                task_type=TaskType.CODING,
                write_permission_level=WritePermissionLevel.WRITE,
                residual_risk_level=RiskLevel.LOW,
                allowed_tools=["edit_files"],
                methodology_family="build",
            ),
            executor=Executor(),
        )

        orchestrator_result = result["orchestrator_result"]
        entry = result["journal_entries"][0]
        serialized_entry = str(entry)
        event_names = [event["event_name"] for event in result["dispatch_trace"]]

        self.assertTrue(orchestrator_result["sandbox_triggered"])
        self.assertEqual(orchestrator_result["sandbox_result"]["status"], "success")
        self.assertEqual(orchestrator_result["rollback_result"]["status"], "not_required")
        self.assertIn("on_sandbox_required", event_names)
        self.assertEqual(entry["source"], "sandbox")
        self.assertIn("sandbox_required", entry["tags"])
        self.assertIn("sandbox_success", entry["tags"])
        self.assertNotIn("snapshot_ref", serialized_entry)
        self.assertNotIn("output", serialized_entry)

    def test_scenario_c_sandbox_failure_with_rollback(self) -> None:
        result = run_v03_flow(
            base_dir=self.temp_dir / "scenario_c",
            contract=make_contract(
                task_id="task-v03-c",
                contract_id="contract-v03-c",
                task_type=TaskType.CODING,
                write_permission_level=WritePermissionLevel.WRITE,
                residual_risk_level=RiskLevel.HIGH,
                allowed_tools=["edit_files"],
                methodology_family="build",
                failure_escalation_policy=["failure_tier:execution_error=>debug"],
            ),
            executor=FailingExecutor(),
        )

        orchestrator_result = result["orchestrator_result"]
        entry = result["journal_entries"][0]
        serialized_entry = str(entry)
        event_names = [event["event_name"] for event in result["dispatch_trace"]]

        self.assertTrue(orchestrator_result["sandbox_triggered"])
        self.assertEqual(orchestrator_result["sandbox_result"]["status"], "error")
        self.assertEqual(orchestrator_result["rollback_result"]["status"], "rolled_back")
        self.assertIn("on_sandbox_required", event_names)
        self.assertEqual(entry["source"], "rollback")
        self.assertIn("rollback_triggered", entry["tags"])
        self.assertNotIn("restored_state", serialized_entry)
        self.assertNotIn("snapshot_ref", serialized_entry)
        self.assertIn("verification_report", orchestrator_result)
        self.assertIn("residual_followup", orchestrator_result)

    def test_scenario_d_high_residual_governance_path_is_advisory_only(self) -> None:
        result = run_v03_flow(
            base_dir=self.temp_dir / "scenario_d",
            contract=make_contract(
                task_id="task-v03-d",
                contract_id="contract-v03-d",
                task_type=TaskType.PLANNING,
                write_permission_level=WritePermissionLevel.READ,
                residual_risk_level=RiskLevel.LOW,
                allowed_tools=["search"],
                methodology_family="architecture",
            ),
            executor=FailingExecutor(),
        )

        orchestrator_result = result["orchestrator_result"]
        event_names = [event["event_name"] for event in result["dispatch_trace"]]
        governance = orchestrator_result["residual_followup"]["governance"]

        self.assertIn("on_verification_report", event_names)
        self.assertIn("on_residual_followup", event_names)
        self.assertIn("on_governance_check", event_names)
        self.assertEqual(orchestrator_result["residual_followup"]["auto_execution"], "none")
        self.assertIsNotNone(orchestrator_result["residual_followup"]["methodology_suggestion"])
        self.assertIsNotNone(orchestrator_result["residual_followup"]["model_suggestion"])
        self.assertTrue(governance["requires_governance_override"])
        self.assertEqual(governance["issues"][0]["code"], "methodology_out_of_contract")


if __name__ == "__main__":
    unittest.main()


