from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest

from harness.state.models import TaskBlock
from harness.state.state_manager import StateManager


class ResidualWritebackPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_dir = Path("tests") / f"_tmp_residual_writeback_{uuid4().hex}"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.storage_dir, ignore_errors=True))
        self.manager = StateManager(self.storage_dir)

    def test_residual_followup_is_persisted_to_task_block(self) -> None:
        saved = self.manager.save_task_block(
            TaskBlock(
                task_id="task-1",
                current_goal="Handle residual follow-up",
                contract_id="contract-1",
            )
        )

        updated = self.manager.apply_residual_writeback(
            {
                "task_id": "task-1",
                "residual_risk": {"reassessed_level": "high", "changed": True},
                "followup_required": True,
                "governance_required": False,
            },
            expected_version=saved.version,
        )

        self.assertEqual(updated.value.residual_risk, {"reassessed_level": "high", "changed": True})
        self.assertTrue(updated.value.followup_required)
        self.assertFalse(updated.value.governance_required)

    def test_required_residual_fields_are_all_persisted(self) -> None:
        saved = self.manager.save_task_block(
            TaskBlock(task_id="task-2", current_goal="Persist risk summary")
        )

        self.manager.apply_residual_writeback(
            {
                "task_id": "task-2",
                "residual_risk": {"reassessed_level": "medium"},
                "followup_required": False,
                "governance_required": True,
            },
            expected_version=saved.version,
        )
        loaded = self.manager.load_task_block("task-2")

        self.assertEqual(loaded.value.residual_risk, {"reassessed_level": "medium"})
        self.assertFalse(loaded.value.followup_required)
        self.assertTrue(loaded.value.governance_required)

    def test_writeback_failures_are_explicit(self) -> None:
        saved = self.manager.save_task_block(
            TaskBlock(task_id="task-3", current_goal="Reject incomplete writeback")
        )

        with self.assertRaisesRegex(ValueError, "missing required field"):
            self.manager.apply_residual_writeback(
                {
                    "task_id": "task-3",
                    "residual_risk": {"reassessed_level": "high"},
                    "followup_required": True,
                },
                expected_version=saved.version,
            )

    def test_writeback_is_visible_on_next_read(self) -> None:
        saved = self.manager.save_task_block(
            TaskBlock(task_id="task-4", current_goal="Carry residual state forward")
        )

        self.manager.apply_residual_writeback(
            {
                "task_id": "task-4",
                "residual_risk": {"reassessed_level": "high", "reason_codes": ["execution_failed"]},
                "followup_required": True,
                "governance_required": True,
            },
            expected_version=saved.version,
        )
        loaded = self.manager.load_task_block("task-4")

        self.assertEqual(loaded.value.residual_risk["reassessed_level"], "high")
        self.assertTrue(loaded.value.followup_required)
        self.assertTrue(loaded.value.governance_required)

    def test_writeback_does_not_expand_into_history_system(self) -> None:
        saved = self.manager.save_task_block(
            TaskBlock(task_id="task-5", current_goal="Keep state schema minimal")
        )

        self.manager.apply_residual_writeback(
            {
                "task_id": "task-5",
                "residual_risk": {"reassessed_level": "low"},
                "followup_required": False,
                "governance_required": False,
            },
            expected_version=saved.version,
        )
        loaded = self.manager.load_task_block("task-5")

        self.assertFalse(hasattr(loaded.value, "history"))
        self.assertFalse(hasattr(loaded.value, "journal"))


if __name__ == "__main__":
    unittest.main()
