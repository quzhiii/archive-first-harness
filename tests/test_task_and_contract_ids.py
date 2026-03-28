from __future__ import annotations

import unittest

from harness.state.models import TaskContract
from planner.task_contract_builder import TaskContractBuilder


class TaskAndContractIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = TaskContractBuilder()

    def test_builder_generates_distinct_task_and_contract_ids(self) -> None:
        contract = self.builder.build("Implement a task contract builder patch.")

        self.assertTrue(contract.task_id)
        self.assertTrue(contract.contract_id)
        self.assertNotEqual(contract.task_id, contract.contract_id)

    def test_task_contract_remains_compatible_without_explicit_task_id(self) -> None:
        contract = TaskContract(
            contract_id="contract-manual-1",
            goal="Review the implementation.",
            success_criteria=["Return a review summary."],
            allowed_tools=["read_files"],
            stop_conditions=["Stop when the file is missing."],
            expected_artifacts=["audit_note"],
        )

        self.assertTrue(contract.task_id)
        self.assertEqual(contract.contract_id, "contract-manual-1")

    def test_same_task_lifecycle_can_hold_multiple_contract_versions(self) -> None:
        first = self.builder.build(
            "Implement the state patch.",
            constraints={"task_id": "task-shared-42"},
        )
        second = self.builder.build(
            "Implement the state patch with a narrower scope.",
            constraints={"task_id": "task-shared-42"},
        )

        self.assertEqual(first.task_id, "task-shared-42")
        self.assertEqual(second.task_id, "task-shared-42")
        self.assertNotEqual(first.contract_id, second.contract_id)


if __name__ == "__main__":
    unittest.main()
