from __future__ import annotations

import unittest

from harness.state.models import BudgetLevel, RiskLevel, TaskContract, TaskType, WritePermissionLevel
from runtime.methodology_router import MethodologyRouter


DEFAULT_METHOD_BY_TASK_TYPE = {
    TaskType.CODING: "build",
    TaskType.EXECUTION: "build",
    TaskType.GENERATION: "build",
    TaskType.RESEARCH: "research",
    TaskType.RETRIEVAL: "research",
    TaskType.PLANNING: "architecture",
    TaskType.REVIEW: "debug",
    TaskType.QA: "debug",
}


def make_contract(
    *,
    task_type: TaskType = TaskType.CODING,
    methodology_family: str | None = None,
    failure_escalation_policy: list[str] | None = None,
) -> TaskContract:
    return TaskContract(
        contract_id="contract-test",
        goal="Test methodology routing",
        success_criteria=["Return a valid methodology decision."],
        allowed_tools=["search"],
        stop_conditions=["Stop if the task is invalid."],
        expected_artifacts=["answer"],
        task_type=task_type,
        write_permission_level=WritePermissionLevel.READ,
        token_budget=BudgetLevel.LOW,
        latency_budget=BudgetLevel.LOW,
        uncertainty_level=RiskLevel.LOW,
        residual_risk_level=RiskLevel.LOW,
        methodology_family=methodology_family or DEFAULT_METHOD_BY_TASK_TYPE[task_type],
        failure_escalation_policy=failure_escalation_policy or [],
    )


class MethodologyRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = MethodologyRouter()

    def test_different_task_types_select_different_methodologies(self) -> None:
        coding_contract = make_contract(task_type=TaskType.CODING)
        research_contract = make_contract(task_type=TaskType.RETRIEVAL)
        planning_contract = make_contract(task_type=TaskType.PLANNING)

        coding_decision = self.router.route(coding_contract)
        research_decision = self.router.route(research_contract)
        planning_decision = self.router.route(planning_contract)

        self.assertEqual(coding_decision["selected_methodology"], "build")
        self.assertEqual(research_decision["selected_methodology"], "research")
        self.assertEqual(planning_decision["selected_methodology"], "architecture")

    def test_contract_failure_policy_switches_methodology_when_matched(self) -> None:
        contract = make_contract(
            task_type=TaskType.CODING,
            methodology_family="build",
            failure_escalation_policy=["failure_tier:tool_failure=>debug"],
        )

        decision = self.router.route(contract, failure_tier="tool_failure")

        self.assertEqual(decision["selected_methodology"], "debug")
        self.assertEqual(
            decision["selection_reason"],
            "contract_failure_policy:failure_tier:tool_failure",
        )
        self.assertTrue(decision["is_within_contract"])
        self.assertFalse(decision["requires_governance_override"])

    def test_unmatched_failure_uses_fallback_methodology(self) -> None:
        contract = make_contract(task_type=TaskType.CODING, methodology_family="build")

        decision = self.router.route(contract, tool_outcome="error")

        self.assertEqual(decision["selected_methodology"], "debug")
        self.assertEqual(decision["selection_reason"], "fallback_debug_for_failure_signal")
        self.assertTrue(decision["is_within_contract"])
        self.assertEqual(decision["expected_next_action"], "switch_to_debug")

    def test_out_of_contract_choice_requires_governance_override(self) -> None:
        contract = make_contract(task_type=TaskType.PLANNING, methodology_family="architecture")

        decision = self.router.route(contract, tool_outcome="error")

        self.assertEqual(decision["selected_methodology"], "debug")
        self.assertFalse(decision["is_within_contract"])
        self.assertTrue(decision["requires_governance_override"])
        self.assertEqual(
            decision["expected_next_action"],
            "request_governance_override_for_debug",
        )

    def test_output_shape_is_complete(self) -> None:
        contract = make_contract(task_type=TaskType.RESEARCH, methodology_family="research")

        decision = self.router.route(
            contract,
            evidence_quality="low",
            context_health="healthy",
            budget_remaining="medium",
        )

        self.assertEqual(
            sorted(decision.keys()),
            sorted(
                [
                    "selected_methodology",
                    "selection_reason",
                    "is_within_contract",
                    "requires_governance_override",
                    "expected_next_action",
                ]
            ),
        )
        self.assertEqual(decision["selected_methodology"], "research")


if __name__ == "__main__":
    unittest.main()
