from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest

from harness.context.context_engine import ContextEngine
from harness.governance.policy import GovernancePolicy
from harness.state.models import BudgetLevel, RiskLevel, TaskBlock, TaskContract, TaskType, WritePermissionLevel
from harness.state.state_manager import StateManager
from harness.tools.tool_discovery_service import ToolDiscoveryService
from runtime.methodology_router import MethodologyRouter
from runtime.model_router import ModelRouter
from runtime.orchestrator import Orchestrator
from runtime.executor import Executor
from runtime.verifier import Verifier


class FailingExecutor:
    def execute_step(self, step, available_tools, working_context):
        return {
            "status": "error",
            "tool_name": step.get("tool_name"),
            "output": None,
            "error": {
                "type": "execution_error",
                "message": "forced failure for residual risk test",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


def make_contract(
    *,
    task_type: TaskType = TaskType.RETRIEVAL,
    methodology_family: str = "research",
    residual_risk_level: RiskLevel = RiskLevel.LOW,
    failure_escalation_policy: list[str] | None = None,
) -> TaskContract:
    return TaskContract(
        contract_id="contract-test",
        goal="Run residual risk loop",
        success_criteria=["Produce a valid result."],
        allowed_tools=["search", "read_files"],
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


class ResidualRiskLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_dir = Path("tests") / f"_tmp_residual_{uuid4().hex}"
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

    def _save_task(self, contract: TaskContract) -> None:
        self.state_manager.save_task_block(
            TaskBlock(
                task_id=contract.contract_id,
                current_goal=contract.goal,
                contract_id=contract.contract_id,
                next_steps=["Run the task."],
            )
        )

    def test_low_risk_stays_low_after_clean_execution(self) -> None:
        contract = make_contract(
            task_type=TaskType.RETRIEVAL,
            methodology_family="research",
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
            methodology_router=self.methodology_router,
            model_router=self.model_router,
            governance_policy=self.governance_policy,
        )

        reassessment = result["residual_followup"]["reassessment"]
        self.assertEqual(reassessment["previous_level"], "low")
        self.assertEqual(reassessment["reassessed_level"], "low")
        self.assertFalse(reassessment["changed"])
        self.assertIsNone(result["residual_followup"]["methodology_suggestion"])
        self.assertIsNone(result["residual_followup"]["model_suggestion"])

    def test_low_risk_can_be_reassessed_to_high(self) -> None:
        contract = make_contract(
            task_type=TaskType.CODING,
            methodology_family="build",
            residual_risk_level=RiskLevel.LOW,
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
        )

        reassessment = result["residual_followup"]["reassessment"]
        self.assertEqual(reassessment["previous_level"], "low")
        self.assertEqual(reassessment["reassessed_level"], "high")
        self.assertTrue(reassessment["changed"])

    def test_verifier_outputs_structured_residual_risk_reassessment(self) -> None:
        contract = make_contract()
        execution_result = {
            "status": "success",
            "tool_name": "search_docs",
            "output": {"summary": "ok"},
            "error": None,
            "artifacts": [],
            "metadata": {},
        }
        verification_report = self.verifier.verify_execution_result(execution_result, contract)

        reassessment = self.verifier.reassess_residual_risk(
            execution_result,
            contract,
            verification_report,
        )

        self.assertEqual(
            sorted(reassessment.keys()),
            sorted(
                [
                    "status",
                    "previous_level",
                    "reassessed_level",
                    "changed",
                    "needs_followup",
                    "reason_codes",
                    "failure_tier",
                    "tool_outcome",
                    "evidence_quality",
                    "context_health",
                    "budget_remaining",
                    "metadata",
                ]
            ),
        )
        self.assertEqual(reassessment["status"], "ok")

    def test_escalations_remain_advisory_only(self) -> None:
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
        )

        self.assertEqual(result["execution_result"]["status"], "error")
        self.assertEqual(result["residual_followup"]["auto_execution"], "none")
        self.assertEqual(
            result["residual_followup"]["methodology_suggestion"]["selected_methodology"],
            "debug",
        )
        self.assertIn(
            result["residual_followup"]["model_suggestion"]["selected_slot"],
            {"strong", "escalated"},
        )

    def test_governance_detects_out_of_contract_followup(self) -> None:
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
        )

        governance = result["residual_followup"]["governance"]
        self.assertTrue(governance["requires_governance_override"])
        self.assertEqual(governance["issues"][0]["code"], "methodology_out_of_contract")

    def test_residual_risk_result_is_written_to_writeback_payload(self) -> None:
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
        )

        writeback = result["state_writeback_payload"]
        self.assertIn("residual_risk", writeback)
        self.assertEqual(writeback["residual_risk"]["reassessed_level"], "high")
        self.assertTrue(writeback["followup_required"])


if __name__ == "__main__":
    unittest.main()
