from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import json
import unittest

from harness.context.context_engine import ContextEngine
from harness.governance.policy import GovernancePolicy
from harness.hooks.hook_orchestrator import HookOrchestrator
from harness.journal.learning_journal import LearningJournal
from harness.sandbox.rollback import RollbackManager
from harness.sandbox.sandbox_executor import SandboxExecutor
from harness.state.models import BudgetLevel, RiskLevel, TaskBlock, TaskContract, TaskType, WritePermissionLevel
from harness.state.state_manager import StateManager
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
                "message": "forced failure for runtime evaluation integration",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


class BuildOnlyContextEngine:
    def __init__(self) -> None:
        self._delegate = ContextEngine()

    def build_working_context(self, *args, **kwargs):
        return self._delegate.build_working_context(*args, **kwargs)


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
    workflow_profile_id: str = "default_general",
) -> TaskContract:
    return TaskContract(
        task_id=task_id,
        contract_id=contract_id,
        goal=f"Run {task_id} evaluation flow",
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
        workflow_profile_id=workflow_profile_id,
    )


def load_baseline_artifacts(*artifact_names: str) -> dict[str, dict[str, object]]:
    artifact_dir = Path("artifacts") / "baselines" / "v03"
    loaded: dict[str, dict[str, object]] = {}
    for artifact_name in artifact_names:
        payload = json.loads((artifact_dir / artifact_name).read_text(encoding="utf-8"))
        key = artifact_name.replace("success_", "").replace(".json", "")
        loaded[key] = payload
    return loaded


def run_runtime_flow(
    *,
    base_dir: Path,
    contract: TaskContract,
    executor,
    learning_journal_enabled: bool = True,
    context_engine=None,
    baseline_artifacts: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    state_manager = StateManager(base_dir / "state")
    state_manager.save_task_block(
        TaskBlock(
            task_id=contract.task_id,
            current_goal=contract.goal,
            contract_id=contract.contract_id,
            next_steps=["Run the runtime evaluation integration path."],
        )
    )

    hooks = HookOrchestrator()
    rollback_manager = RollbackManager()
    sandbox_executor = SandboxExecutor(rollback_manager)
    journal = LearningJournal(base_dir / "learning_journal.jsonl") if learning_journal_enabled else None

    return Orchestrator().run(
        contract,
        state_manager,
        context_engine or ContextEngine(),
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
        baseline_artifacts=baseline_artifacts,
    )


class RuntimeEvaluationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_runtime_eval_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))

    def test_real_run_produces_bundle_and_realm_evaluation(self) -> None:
        result = run_runtime_flow(
            base_dir=self.temp_dir / "success",
            contract=make_contract(
                task_id="task-runtime-eval-1",
                contract_id="contract-runtime-eval-1",
                task_type=TaskType.RETRIEVAL,
                write_permission_level=WritePermissionLevel.READ,
                residual_risk_level=RiskLevel.LOW,
                allowed_tools=["search", "read_files"],
                methodology_family="research",
            ),
            executor=Executor(),
        )

        bundle = result["evaluation_input_bundle"]
        self.assertIn("evaluation_input_bundle", result)
        self.assertIn("realm_evaluation", result)
        self.assertIn("baseline_compare_results", result)
        self.assertIn("block_selection_report", result)
        self.assertIn("metrics_summary", result)
        self.assertEqual(result["execution_result"]["status"], "success")
        self.assertEqual(result["verification_report"]["status"], "passed")
        self.assertEqual(result["baseline_compare_results"]["status"], "not_requested")
        self.assertTrue(bundle["event_trace_summary"]["key_events"]["on_verification_report"])
        self.assertTrue(bundle["journal_append_summary"]["append_happened"])
        self.assertEqual(result["realm_evaluation"]["status"], "ok")
        self.assertEqual(result["realm_evaluation"]["metadata"]["automatic_action"], "none")
        self.assertNotIn("allowed_tools", bundle["task_contract_summary"])
        self.assertNotIn("dispatch_trace", bundle["event_trace_summary"])
        self.assertNotIn("learning_journal", bundle["journal_append_summary"])

    def test_bundle_build_is_stable_when_block_report_or_journal_trace_are_missing(self) -> None:
        result = run_runtime_flow(
            base_dir=self.temp_dir / "missing_optional_inputs",
            contract=make_contract(
                task_id="task-runtime-eval-2",
                contract_id="contract-runtime-eval-2",
                task_type=TaskType.RETRIEVAL,
                write_permission_level=WritePermissionLevel.READ,
                residual_risk_level=RiskLevel.LOW,
                allowed_tools=["search", "read_files"],
                methodology_family="research",
            ),
            executor=Executor(),
            learning_journal_enabled=False,
            context_engine=BuildOnlyContextEngine(),
        )

        bundle = result["evaluation_input_bundle"]
        self.assertEqual(result["learning_journal"]["status"], "disabled")
        self.assertEqual(bundle["block_selection_report"]["included_blocks"], [])
        self.assertFalse(bundle["journal_append_summary"]["append_happened"])
        self.assertEqual(bundle["event_trace_summary"]["event_count"], 1)
        self.assertEqual(result["realm_evaluation"]["metadata"]["automatic_action"], "none")

    def test_baseline_compare_links_from_real_runtime_bundle(self) -> None:
        baselines = load_baseline_artifacts(
            "success_verification_report.json",
            "success_residual_followup.json",
            "success_metrics_summary.json",
        )
        result = run_runtime_flow(
            base_dir=self.temp_dir / "baseline_compare",
            contract=make_contract(
                task_id="task-runtime-eval-3",
                contract_id="contract-runtime-eval-3",
                task_type=TaskType.RETRIEVAL,
                write_permission_level=WritePermissionLevel.READ,
                residual_risk_level=RiskLevel.LOW,
                allowed_tools=["search", "read_files"],
                methodology_family="research",
                workflow_profile_id="evaluation_regression",
            ),
            executor=Executor(),
            baseline_artifacts=baselines,
        )

        compare_results = result["baseline_compare_results"]
        metrics_compare_metadata = compare_results["artifact_results"]["metrics_summary"]["metadata"]
        self.assertEqual(compare_results["status"], "completed")
        self.assertEqual(
            compare_results["artifact_results"]["verification_report"]["status"],
            "compatible",
        )
        self.assertEqual(
            compare_results["artifact_results"]["residual_followup"]["status"],
            "compatible",
        )
        self.assertIn(
            compare_results["artifact_results"]["metrics_summary"]["status"],
            {"compatible", "warning"},
        )
        self.assertEqual(metrics_compare_metadata["workflow_profile_id"], "evaluation_regression")
        self.assertEqual(
            metrics_compare_metadata["comparison_focus"],
            result["realm_evaluation"]["metadata"]["comparison_focus"],
        )
        self.assertEqual(
            metrics_compare_metadata["artifact_relevance_hint"],
            result["realm_evaluation"]["metadata"]["artifact_relevance_hint"],
        )
        self.assertEqual(result["execution_result"]["status"], "success")

    def test_real_run_keeps_profile_summary_without_new_control_branch(self) -> None:
        result = run_runtime_flow(
            base_dir=self.temp_dir / "profile_summary",
            contract=make_contract(
                task_id="task-runtime-eval-profile",
                contract_id="contract-runtime-eval-profile",
                task_type=TaskType.REVIEW,
                write_permission_level=WritePermissionLevel.READ,
                residual_risk_level=RiskLevel.LOW,
                allowed_tools=["read_files"],
                methodology_family="compliance",
                workflow_profile_id="evaluation_regression",
            ),
            executor=Executor(),
        )

        task_summary = result["evaluation_input_bundle"]["task_contract_summary"]
        self.assertEqual(task_summary["workflow_profile_id"], "evaluation_regression")
        self.assertEqual(task_summary["intent_class"], "evaluation")
        self.assertEqual(result["realm_evaluation"]["metadata"]["workflow_profile_id"], "evaluation_regression")
        self.assertEqual(result["realm_evaluation"]["metadata"]["automatic_action"], "none")
        self.assertIn(result["execution_result"]["status"], {"success", "error"})
        self.assertFalse(result["sandbox_triggered"])

    def test_compare_and_realm_outputs_do_not_become_runtime_controllers(self) -> None:
        baselines = load_baseline_artifacts("success_verification_report.json")
        result = run_runtime_flow(
            base_dir=self.temp_dir / "advisory_only",
            contract=make_contract(
                task_id="task-runtime-eval-4",
                contract_id="contract-runtime-eval-4",
                task_type=TaskType.PLANNING,
                write_permission_level=WritePermissionLevel.READ,
                residual_risk_level=RiskLevel.LOW,
                allowed_tools=["search"],
                methodology_family="architecture",
                failure_escalation_policy=["failure_tier:execution_error=>debug"],
            ),
            executor=FailingExecutor(),
            baseline_artifacts=baselines,
        )

        compare_results = result["baseline_compare_results"]
        self.assertEqual(result["execution_result"]["status"], "error")
        self.assertEqual(result["residual_followup"]["auto_execution"], "none")
        self.assertIn(
            compare_results["artifact_results"]["verification_report"]["status"],
            {"warning", "breaking"},
        )
        self.assertEqual(result["realm_evaluation"]["metadata"]["automatic_action"], "none")
        self.assertTrue(result["realm_evaluation"]["requires_human_review"])
        self.assertFalse(result["sandbox_triggered"])


if __name__ == "__main__":
    unittest.main()
