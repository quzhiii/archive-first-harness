import unittest
from unittest.mock import patch

from harness.contracts.profile_input_adapter import ProfileInputResolution
from harness.state.models import (
    BudgetLevel,
    RiskLevel,
    TASK_CONTRACT_SCHEMA_VERSION,
    TaskContract,
    TaskType,
    WritePermissionLevel,
)
from planner.task_contract_builder import TaskContractBuilder


class TaskContractBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = TaskContractBuilder()

    def test_build_returns_task_contract_with_required_fields(self) -> None:
        contract = self.builder.build("Implement a minimal task contract builder for the planner.")

        self.assertIsInstance(contract, TaskContract)
        self.assertTrue(contract.contract_id)
        self.assertEqual(contract.schema_version, TASK_CONTRACT_SCHEMA_VERSION)
        self.assertEqual(contract.task_type, TaskType.CODING)
        self.assertEqual(contract.write_permission_level, WritePermissionLevel.WRITE)
        self.assertTrue(contract.success_criteria)
        self.assertTrue(contract.allowed_tools)
        self.assertTrue(contract.stop_conditions)
        self.assertTrue(contract.expected_artifacts)

    def test_builder_uses_conservative_defaults_when_information_is_sparse(self) -> None:
        contract = self.builder.build("Help.")

        self.assertEqual(contract.task_type, TaskType.GENERATION)
        self.assertEqual(contract.write_permission_level, WritePermissionLevel.PROPOSE)
        self.assertEqual(contract.token_budget, BudgetLevel.LOW)
        self.assertEqual(contract.latency_budget, BudgetLevel.LOW)
        self.assertEqual(contract.retrieval_budget, BudgetLevel.LOW)
        self.assertEqual(contract.verification_budget, BudgetLevel.LOW)
        self.assertEqual(contract.escalation_budget, BudgetLevel.LOW)
        self.assertEqual(contract.uncertainty_level, RiskLevel.MEDIUM)
        self.assertEqual(contract.residual_risk_level, RiskLevel.LOW)

    def test_builder_never_returns_empty_success_criteria(self) -> None:
        contract = self.builder.build("Review the current draft.")

        self.assertGreater(len(contract.success_criteria), 0)
        self.assertTrue(all(item.strip() for item in contract.success_criteria))

    def test_builder_honors_explicit_overrides(self) -> None:
        contract = self.builder.build(
            "Search project notes for context.",
            constraints={
                "success_criteria": ["Return only notes tagged runtime."],
                "allowed_tools": ["search_notes"],
                "write_permission_level": "query",
                "token_budget": "medium",
                "latency_budget": "medium",
                "retrieval_budget": "medium",
                "verification_budget": "low",
                "escalation_budget": "low",
                "uncertainty_level": "low",
                "residual_risk_level": "low",
                "expected_artifacts": ["answer"],
                "stop_conditions": ["No matching note is available."],
            },
        )

        self.assertEqual(contract.success_criteria, ["Return only notes tagged runtime."])
        self.assertEqual(contract.allowed_tools, ["search_notes"])
        self.assertEqual(contract.write_permission_level, WritePermissionLevel.QUERY)
        self.assertEqual(contract.token_budget, BudgetLevel.MEDIUM)
        self.assertEqual(contract.latency_budget, BudgetLevel.MEDIUM)
        self.assertEqual(contract.retrieval_budget, BudgetLevel.MEDIUM)
        self.assertEqual(contract.verification_budget, BudgetLevel.LOW)
        self.assertEqual(contract.escalation_budget, BudgetLevel.LOW)
        self.assertEqual(contract.expected_artifacts, ["answer"])
        self.assertEqual(contract.stop_conditions, ["No matching note is available."])

    def test_builder_uses_shared_profile_input_adapter(self) -> None:
        with patch("planner.task_contract_builder.resolve_surface_workflow_profile") as resolve_mock:
            resolve_mock.return_value = ProfileInputResolution(
                workflow_profile_id="planning_design",
                source="workflow_profile",
                used_fallback=False,
                fallback_reason=None,
            )

            contract = self.builder.build(
                "Design a runtime harness plan.",
                constraints={"workflow_profile": "planning-design"},
            )

        resolve_mock.assert_called_once()
        _, kwargs = resolve_mock.call_args
        self.assertEqual(kwargs["task_type"], TaskType.PLANNING)
        self.assertEqual(contract.workflow_profile_id, "planning_design")

    def test_builder_keeps_only_normalized_workflow_profile_id(self) -> None:
        contract = self.builder.build(
            "Implement a runtime harness patch.",
            constraints={"mission_profile_id": "Implementation-Build"},
        )

        self.assertEqual(contract.workflow_profile_id, "implementation_build")
        self.assertFalse(hasattr(contract, "workflow_profile"))
        self.assertFalse(hasattr(contract, "mission_profile_id"))


if __name__ == "__main__":
    unittest.main()
