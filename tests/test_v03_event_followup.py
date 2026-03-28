from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest

from harness.context.context_engine import ContextEngine
from harness.governance.policy import GovernancePolicy
from harness.hooks.hook_orchestrator import HookDispatchError, HookOrchestrator
from harness.hooks.models import (
    GovernanceCheckPayload,
    ResidualFollowupPayload,
    VerificationReportPayload,
)
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
                "message": "forced failure for event follow-up test",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


def make_contract(
    *,
    task_type: TaskType = TaskType.CODING,
    methodology_family: str = "build",
    residual_risk_level: RiskLevel = RiskLevel.LOW,
    failure_escalation_policy: list[str] | None = None,
) -> TaskContract:
    return TaskContract(
        contract_id=f"contract-{uuid4().hex}",
        goal="Run v0.3 event follow-up path",
        success_criteria=["Produce a valid structured result."],
        allowed_tools=["search", "read_files", "run_tests"],
        stop_conditions=["Stop when the result is invalid."],
        expected_artifacts=["answer"],
        task_type=task_type,
        write_permission_level=WritePermissionLevel.READ,
        token_budget=BudgetLevel.LOW,
        latency_budget=BudgetLevel.LOW,
        uncertainty_level=RiskLevel.LOW,
        residual_risk_level=residual_risk_level,
        methodology_family=methodology_family,
        failure_escalation_policy=failure_escalation_policy or [],
    )


class V03EventFollowupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_dir = Path("tests") / f"_tmp_v03_followup_{uuid4().hex}"
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
        self.hooks = HookOrchestrator()

    def _save_task(self, contract: TaskContract) -> None:
        self.state_manager.save_task_block(
            TaskBlock(
                task_id=contract.task_id,
                current_goal=contract.goal,
                contract_id=contract.contract_id,
                next_steps=["Run the eventized advisory chain."],
            )
        )

    def test_verification_report_emits_event(self) -> None:
        captured: list[VerificationReportPayload] = []
        self.hooks.register("on_verification_report", captured.append)
        contract = make_contract(task_type=TaskType.RETRIEVAL, methodology_family="research")
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            hook_orchestrator=self.hooks,
        )

        self.assertEqual(len(captured), 1)
        payload = captured[0]
        self.assertEqual(payload.task_id, contract.task_id)
        self.assertEqual(payload.contract_id, contract.contract_id)
        self.assertEqual(payload.verification_report, result["verification_report"])
        self.assertEqual(payload.residual_risk_hint, result["verification_report"]["residual_risk_hint"])
        self.assertEqual(payload.schema_version, "v0.3")

    def test_residual_followup_emits_event_when_needed(self) -> None:
        captured: list[ResidualFollowupPayload] = []
        self.hooks.register("on_residual_followup", captured.append)
        contract = make_contract(
            task_type=TaskType.CODING,
            methodology_family="build",
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
            hook_orchestrator=self.hooks,
        )

        self.assertEqual(len(captured), 1)
        payload = captured[0]
        self.assertEqual(payload.task_id, contract.task_id)
        self.assertEqual(payload.contract_id, contract.contract_id)
        self.assertTrue(payload.residual_reassessment["needs_followup"])
        self.assertEqual(payload.methodology_advice["selected_methodology"], "debug")
        self.assertIn(payload.model_advice["selected_slot"], {"strong", "escalated"})
        self.assertEqual(result["residual_followup"]["auto_execution"], "none")

    def test_governance_check_emits_when_boundary_risk_exists(self) -> None:
        captured: list[GovernanceCheckPayload] = []
        self.hooks.register("on_governance_check", captured.append)
        contract = make_contract(
            task_type=TaskType.PLANNING,
            methodology_family="architecture",
            residual_risk_level=RiskLevel.LOW,
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
            hook_orchestrator=self.hooks,
        )

        self.assertEqual(len(captured), 1)
        payload = captured[0]
        self.assertEqual(payload.task_id, contract.task_id)
        self.assertEqual(payload.contract_id, contract.contract_id)
        self.assertTrue(payload.governance_required)
        self.assertEqual(payload.advice_summary["methodology_advice"]["selected_methodology"], "debug")
        self.assertIn("methodology_out_of_contract", payload.advice_summary["issue_codes"])
        self.assertTrue(result["residual_followup"]["governance"]["requires_governance_override"])

    def test_governance_only_identifies_boundary_and_does_not_auto_execute(self) -> None:
        contract = make_contract(
            task_type=TaskType.PLANNING,
            methodology_family="architecture",
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
            hook_orchestrator=self.hooks,
        )

        governance = result["residual_followup"]["governance"]
        self.assertEqual(result["residual_followup"]["auto_execution"], "none")
        self.assertEqual(governance["status"], "review_required")
        self.assertTrue(governance["requires_governance_override"])
        self.assertEqual(governance["issues"][0]["code"], "methodology_out_of_contract")

    def test_main_output_stays_complete_and_writeback_payload_is_preserved(self) -> None:
        contract = make_contract(
            task_type=TaskType.CODING,
            methodology_family="build",
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
            hook_orchestrator=self.hooks,
        )

        self.assertIn("execution_result", result)
        self.assertIn("verification_report", result)
        self.assertIn("residual_followup", result)
        self.assertIn("state_writeback_payload", result)
        self.assertEqual(result["state_writeback_payload"]["task_id"], contract.task_id)
        self.assertIn("residual_risk", result["state_writeback_payload"])
        self.assertIn("followup_required", result["state_writeback_payload"])
        self.assertIn("governance_required", result["state_writeback_payload"])

    def test_handler_failure_is_fail_fast_and_trace_is_visible(self) -> None:
        def fail_on_verification(payload: VerificationReportPayload) -> None:
            raise RuntimeError("verification hook failed")

        self.hooks.register("on_verification_report", fail_on_verification)
        contract = make_contract(task_type=TaskType.RETRIEVAL, methodology_family="research")
        self._save_task(contract)

        with self.assertRaises(HookDispatchError):
            self.orchestrator.run(
                contract,
                self.state_manager,
                self.context_engine,
                None,
                self.tool_discovery,
                Executor(),
                verifier=self.verifier,
                hook_orchestrator=self.hooks,
            )

        trace = self.hooks.get_recent_dispatches(limit=1)[0]
        self.assertEqual(trace["event_name"], "on_verification_report")
        self.assertEqual(trace["status"], "failed")
        self.assertEqual(trace["error_type"], "RuntimeError")

    def test_dispatch_trace_contains_key_event_names(self) -> None:
        contract = make_contract(
            task_type=TaskType.PLANNING,
            methodology_family="architecture",
        )
        self._save_task(contract)

        self.orchestrator.run(
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
            hook_orchestrator=self.hooks,
        )

        event_names = [dispatch["event_name"] for dispatch in self.hooks.get_recent_dispatches()]
        self.assertIn("on_verification_report", event_names)
        self.assertIn("on_residual_followup", event_names)
        self.assertIn("on_governance_check", event_names)


if __name__ == "__main__":
    unittest.main()
