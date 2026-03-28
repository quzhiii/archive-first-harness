from __future__ import annotations

import unittest

from harness.sandbox.rollback import RollbackManager
from harness.sandbox.sandbox_executor import SandboxExecutor


class SandboxExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rollback_manager = RollbackManager()
        self.executor = SandboxExecutor(self.rollback_manager)

    def test_executes_mock_action_and_returns_structured_result(self) -> None:
        result = self.executor.execute("write_preview", {"path": "notes.txt"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["action"], "write_preview")
        self.assertEqual(result["payload"], {"path": "notes.txt"})
        self.assertIsNotNone(result["output"])
        self.assertTrue(result["snapshot_ref"])

    def test_failed_action_returns_explicit_error(self) -> None:
        result = self.executor.execute("write_preview", {"should_fail": True})

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["type"], "sandbox_execution_failed")
        self.assertTrue(result["snapshot_ref"])

    def test_can_create_snapshot_reference(self) -> None:
        snapshot_ref = self.executor.snapshot_before("update_state", {"value": "before"})
        description = self.rollback_manager.describe_snapshot(snapshot_ref)

        self.assertTrue(snapshot_ref)
        self.assertEqual(description["status"], "ok")
        self.assertEqual(description["snapshot_ref"], snapshot_ref)

    def test_rollback_can_restore_mock_state(self) -> None:
        target = {"value": "before"}
        snapshot = self.rollback_manager.create_snapshot(target)
        target["value"] = "after"

        result = self.rollback_manager.rollback(snapshot["snapshot_ref"])

        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(target["value"], "before")


if __name__ == "__main__":
    unittest.main()
