from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest

from harness.state.models import GlobalState, ProjectBlock, TaskBlock
from harness.state.state_manager import (
    StateManager,
    StateSnapshot,
    StateVersionConflictError,
)


class StateManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_path = Path("tests") / f"_tmp_state_manager_{uuid4().hex}"
        self.temp_path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_path, ignore_errors=True))
        self.manager = StateManager(self.temp_path)

    def test_loads_default_state_when_files_are_missing(self) -> None:
        global_state = self.manager.load_global_state()
        project_block = self.manager.load_project_block()
        task_block = self.manager.load_task_block("task-1")

        self.assertEqual(global_state.version, 0)
        self.assertEqual(project_block.version, 0)
        self.assertEqual(task_block.version, 0)
        self.assertEqual(project_block.value.project_id, "default")
        self.assertEqual(task_block.value.task_id, "task-1")

    def test_can_save_and_reload_state(self) -> None:
        saved_global_state = self.manager.save_global_state(
            GlobalState(hard_constraints=["Do not overwrite user files."])
        )
        saved_project_block = self.manager.save_project_block(
            ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                current_phase="v0.1",
                goals=["Stabilize the MVP harness."],
            )
        )

        loaded_global_state = self.manager.load_global_state()
        loaded_project_block = self.manager.load_project_block()

        self.assertEqual(saved_global_state.version, 1)
        self.assertEqual(saved_project_block.version, 1)
        self.assertEqual(
            loaded_global_state.value.hard_constraints,
            ["Do not overwrite user files."],
        )
        self.assertEqual(loaded_project_block.value.project_name, "Agent Runtime")

    def test_task_block_update_persists_to_disk(self) -> None:
        saved = self.manager.save_task_block(
            TaskBlock(task_id="task-1", current_goal="Implement state manager"),
        )

        updated = self.manager.update_task_block(
            "task-1",
            {
                "next_steps": ["Add persistence tests."],
                "blockers": ["Need a temporary directory."],
            },
            expected_version=saved.version,
        )

        loaded = self.manager.load_task_block("task-1")
        self.assertEqual(updated.version, 2)
        self.assertEqual(loaded.value.next_steps, ["Add persistence tests."])
        self.assertEqual(loaded.value.blockers, ["Need a temporary directory."])

    def test_rejects_version_conflicts(self) -> None:
        self.manager.save_task_block(
            TaskBlock(task_id="task-1", current_goal="Initial goal"),
        )

        with self.assertRaises(StateVersionConflictError):
            self.manager.save_task_block(
                TaskBlock(task_id="task-1", current_goal="Overwrite goal"),
                expected_version=0,
            )

    def test_update_does_not_clear_existing_values_with_empty_updates(self) -> None:
        saved = self.manager.save_task_block(
            TaskBlock(
                task_id="task-1",
                current_goal="Keep stable facts",
                next_steps=["Write tests."],
                blockers=["Need fixtures."],
            ),
        )

        updated = self.manager.update_task_block(
            "task-1",
            {
                "current_goal": "",
                "next_steps": [],
                "blockers": None,
                "known_risks": ["Version mismatch."],
            },
            expected_version=saved.version,
        )

        self.assertEqual(updated.value.current_goal, "Keep stable facts")
        self.assertEqual(updated.value.next_steps, ["Write tests."])
        self.assertEqual(updated.value.blockers, ["Need fixtures."])
        self.assertEqual(updated.value.known_risks, ["Version mismatch."])

    def test_build_state_snapshot_for_context_returns_minimal_state_set(self) -> None:
        self.manager.save_global_state(
            GlobalState(hard_constraints=["Prefer structured state over chat history."])
        )
        self.manager.save_project_block(
            ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                goals=["Ship B v0.1 state and context support."],
            )
        )
        self.manager.save_task_block(
            TaskBlock(task_id="task-1", current_goal="Assemble a working context"),
        )

        snapshot = self.manager.build_state_snapshot_for_context("task-1")

        self.assertIsInstance(snapshot, StateSnapshot)
        self.assertEqual(snapshot.task_block.task_id, "task-1")
        self.assertEqual(snapshot.project_block.project_id, "agent-runtime")
        self.assertIn("global_state", snapshot.versions)
        self.assertIn("project_block", snapshot.versions)
        self.assertIn("task_block", snapshot.versions)


if __name__ == "__main__":
    unittest.main()
