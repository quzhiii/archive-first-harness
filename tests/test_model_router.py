from __future__ import annotations

import unittest

from harness.state.models import BudgetLevel, RiskLevel, TaskContract, TaskType, WritePermissionLevel
from runtime.model_router import ModelRouter


def make_contract(
    *,
    task_type: TaskType = TaskType.RETRIEVAL,
    token_budget: BudgetLevel = BudgetLevel.LOW,
    latency_budget: BudgetLevel = BudgetLevel.LOW,
    uncertainty_level: RiskLevel = RiskLevel.LOW,
    residual_risk_level: RiskLevel = RiskLevel.LOW,
) -> TaskContract:
    return TaskContract(
        contract_id="contract-test",
        goal="Test routing",
        success_criteria=["Return a valid routing decision."],
        allowed_tools=["search"],
        stop_conditions=["Stop if the task is invalid."],
        expected_artifacts=["answer"],
        task_type=task_type,
        write_permission_level=WritePermissionLevel.READ,
        token_budget=token_budget,
        latency_budget=latency_budget,
        uncertainty_level=uncertainty_level,
        residual_risk_level=residual_risk_level,
    )


class ModelRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = ModelRouter()

    def test_simple_task_uses_low_cost_slot(self) -> None:
        contract = make_contract()

        decision = self.router.route(contract)

        self.assertEqual(decision["selected_slot"], "cheap")
        self.assertIn("task_type_allows_low_cost_slot", decision["reason_codes"])

    def test_high_uncertainty_can_upgrade_slot(self) -> None:
        contract = make_contract(uncertainty_level=RiskLevel.HIGH)

        decision = self.router.route(contract)

        self.assertEqual(decision["selected_slot"], "balanced")
        self.assertIn("high_uncertainty", decision["reason_codes"])
        self.assertTrue(decision["escalation_allowed"])

    def test_high_residual_risk_can_upgrade_slot(self) -> None:
        contract = make_contract(residual_risk_level=RiskLevel.HIGH)

        decision = self.router.route(contract)

        self.assertEqual(decision["selected_slot"], "balanced")
        self.assertIn("high_residual_risk", decision["reason_codes"])
        self.assertTrue(decision["escalation_allowed"])

    def test_hysteresis_blocks_fast_deescalation(self) -> None:
        contract = make_contract()

        decision = self.router.route(
            contract,
            current_slot="balanced",
            history=[],
        )

        self.assertEqual(decision["selected_slot"], "balanced")
        self.assertTrue(decision["hysteresis_applied"])
        self.assertIn("deescalation_blocked_by_hysteresis", decision["reason_codes"])

    def test_decision_result_has_complete_shape(self) -> None:
        contract = make_contract(
            task_type=TaskType.CODING,
            token_budget=BudgetLevel.HIGH,
            uncertainty_level=RiskLevel.HIGH,
            residual_risk_level=RiskLevel.HIGH,
        )

        decision = self.router.route(contract)

        self.assertEqual(
            sorted(decision.keys()),
            sorted(
                [
                    "selected_slot",
                    "reason_codes",
                    "escalation_allowed",
                    "hysteresis_applied",
                    "metadata",
                ]
            ),
        )
        self.assertEqual(decision["selected_slot"], "escalated")
        self.assertIsInstance(decision["metadata"], dict)


if __name__ == "__main__":
    unittest.main()
