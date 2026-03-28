from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest

from harness.context.context_engine import ContextEngine
from harness.governance.policy import GovernancePolicy
from harness.hooks.hook_orchestrator import HookOrchestrator
from harness.hooks.models import SandboxRequiredPayload
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
                "message": "forced failure for sandbox gate test",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


def make_contract(
    *,
    task_type: TaskType = TaskType.RETRIEVAL,
    write_permission_level: WritePermissionLevel = WritePermissionLevel.READ,
    residual_risk_level: RiskLevel = RiskLevel.LOW,
    allowed_tools: list[str] | None = None,
    failure_escalation_policy: list[str] | None = None,
) -> TaskContract:
    return TaskContract(
        contract_id=f"contract-{uuid4().hex}",
        goal="Run v0.3 sandbox gated execution path",
        success_criteria=["Produce a valid structured result."],
        allowed_tools=allowed_tools or ["search", "read_files"],
        stop_conditions=["Stop when the result is invalid."],
        expected_artifacts=["answer"],
        task_type=task_type,
        write_permission_level=write_permission_level,
        token_budget=BudgetLevel.LOW,
        latency_budget=BudgetLevel.LOW,
        uncertainty_level=RiskLevel.LOW,
        residual_risk_level=residual_risk_level,
        methodology_family="build" if task_type == TaskType.CODING else "research",
        failure_escalation_policy=failure_escalation_policy or [],
    )


class V03SandboxGatedExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_dir = Path("tests") / f"_tmp_v03_sandbox_{uuid4().hex}"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.storage_dir, ignore_errors=True))
        self.state_manager = StateManager(self.storage_dir)
        self.context_engine = ContextEngine()
        self.tool_discovery = ToolDiscoveryService()
        self.orchestrator = Orchestrator()
        self.verifier = Verifier()
        self.methodology_router = MethodologyRouter()
        self.model_router = ModelRouter()
        self.governance_policy = GovernancePolicy()
        self.rollback_manager = RollbackManager()
        self.sandbox_executor = SandboxExecutor(self.rollback_manager)
        self.hooks = HookOrchestrator()

    def _save_task(self, contract: TaskContract) -> None:
        self.state_manager.save_task_block(
            TaskBlock(
                task_id=contract.task_id,
                current_goal=contract.goal,
                contract_id=contract.contract_id,
                next_steps=["Run the sandbox gate path."],
            )
        )

    def test_low_risk_read_path_does_not_trigger_sandbox(self) -> None:
        captured: list[SandboxRequiredPayload] = []
        self.hooks.register("on_sandbox_required", captured.append)
        contract = make_contract(
            task_type=TaskType.RETRIEVAL,
            write_permission_level=WritePermissionLevel.READ,
            residual_risk_level=RiskLevel.LOW,
        )
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            governance_policy=self.governance_policy,
            hook_orchestrator=self.hooks,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        self.assertFalse(result["sandbox_triggered"])
        self.assertEqual(result["sandbox_decision"]["status"], "direct_execution_allowed")
        self.assertIsNone(result["sandbox_result"])
        self.assertEqual(result["rollback_result"]["status"], "not_required")
        self.assertEqual(captured, [])

    def test_high_risk_path_emits_event_and_returns_structured_sandbox_result(self) -> None:
        captured: list[SandboxRequiredPayload] = []
        self.hooks.register("on_sandbox_required", captured.append)
        contract = make_contract(
            task_type=TaskType.RETRIEVAL,
            write_permission_level=WritePermissionLevel.READ,
            residual_risk_level=RiskLevel.HIGH,
        )
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            governance_policy=self.governance_policy,
            hook_orchestrator=self.hooks,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        self.assertTrue(result["sandbox_triggered"])
        self.assertEqual(result["sandbox_decision"]["reason_codes"], ["high_risk_level"])
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].task_id, contract.task_id)
        self.assertEqual(captured[0].risk_level, "high")
        self.assertEqual(result["sandbox_result"]["status"], "success")
        self.assertEqual(result["sandbox_result"]["action"], "execute_step")
        self.assertIn("snapshot_ref", result["sandbox_result"])
        self.assertTrue(result["execution_result"]["metadata"]["sandboxed"])

    def test_high_permission_write_path_triggers_sandbox(self) -> None:
        contract = make_contract(
            task_type=TaskType.CODING,
            write_permission_level=WritePermissionLevel.WRITE,
            residual_risk_level=RiskLevel.LOW,
            allowed_tools=["edit_files"],
        )
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            governance_policy=self.governance_policy,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        self.assertTrue(result["sandbox_triggered"])
        self.assertIn("high_write_permission", result["sandbox_decision"]["reason_codes"])
        self.assertEqual(result["execution_result"]["tool_name"], "write_file")
        self.assertEqual(result["sandbox_result"]["status"], "success")

    def test_sandbox_failure_triggers_minimal_rollback(self) -> None:
        contract = make_contract(
            task_type=TaskType.CODING,
            write_permission_level=WritePermissionLevel.WRITE,
            residual_risk_level=RiskLevel.HIGH,
            allowed_tools=["edit_files"],
            failure_escalation_policy=["failure_tier:execution_error=>debug"],
        )
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            FailingExecutor(),
            verifier=self.verifier,
            methodology_router=self.methodology_router,
            model_router=self.model_router,
            governance_policy=self.governance_policy,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        self.assertTrue(result["sandbox_triggered"])
        self.assertEqual(result["sandbox_result"]["status"], "error")
        self.assertEqual(result["rollback_result"]["status"], "rolled_back")
        self.assertEqual(result["rollback_result"]["restored_state"]["status"], "pending")
        self.assertEqual(result["execution_result"]["status"], "error")
        self.assertEqual(result["residual_followup"]["auto_execution"], "none")

    def test_governance_only_identifies_sandbox_need_and_does_not_auto_approve(self) -> None:
        contract = make_contract(
            task_type=TaskType.EXECUTION,
            write_permission_level=WritePermissionLevel.DESTRUCTIVE_WRITE,
            residual_risk_level=RiskLevel.LOW,
            allowed_tools=["run_command"],
        )

        decision = self.governance_policy.review_execution_gate(
            task_contract=contract,
            action={"tool_name": "run_command"},
        )

        self.assertTrue(decision["sandbox_required"])
        self.assertTrue(decision["governance_required"])
        self.assertIn("governance_requires_isolation", decision["reason_codes"])
        self.assertNotIn("approved", decision)

    def test_main_output_stays_complete_when_sandbox_is_used(self) -> None:
        contract = make_contract(
            task_type=TaskType.RETRIEVAL,
            write_permission_level=WritePermissionLevel.READ,
            residual_risk_level=RiskLevel.HIGH,
        )
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            governance_policy=self.governance_policy,
            hook_orchestrator=self.hooks,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        self.assertIn("execution_result", result)
        self.assertIn("verification_report", result)
        self.assertIn("sandbox_triggered", result)
        self.assertIn("sandbox_decision", result)
        self.assertIn("sandbox_result", result)
        self.assertIn("rollback_result", result)
        self.assertIn("state_writeback_payload", result)


if __name__ == "__main__":
    unittest.main()
