from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest

from harness.context.context_engine import ContextEngine
from harness.journal.learning_journal import LearningJournal
from harness.state.models import TaskBlock
from harness.state.state_manager import StateManager
from harness.tools.tool_discovery_service import ToolDiscoveryService
from planner.task_contract_builder import TaskContractBuilder
from runtime.executor import Executor
from runtime.orchestrator import Orchestrator
from runtime.verifier import Verifier


class LearningJournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_learning_journal_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.store_path = self.temp_dir / "learning_journal.jsonl"
        self.journal = LearningJournal(self.store_path)
        self.builder = TaskContractBuilder()

    def test_can_append_journal_entry(self) -> None:
        entry = self.journal.build_lesson_entry(
            task_id="task-1",
            task_type="coding",
            lesson="Keep parser fixes scoped to the failing module.",
        )
        appended = self.journal.append_lesson(entry)

        self.assertEqual(appended["task_id"], "task-1")
        self.assertTrue(self.store_path.exists())
        self.assertIn("Keep parser fixes scoped", self.store_path.read_text(encoding="utf-8"))

    def test_reads_relevant_lessons_by_task_type(self) -> None:
        self.journal.append_lesson(
            self.journal.build_lesson_entry(task_id="task-1", task_type="coding", lesson="Coding lesson")
        )
        self.journal.append_lesson(
            self.journal.build_lesson_entry(task_id="task-2", task_type="research", lesson="Research lesson")
        )

        lessons = self.journal.read_relevant_lessons(task_type="coding")

        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["task_type"], "coding")

    def test_reads_relevant_lessons_by_tags(self) -> None:
        self.journal.append_lesson(
            self.journal.build_lesson_entry(
                task_id="task-1",
                task_type="coding",
                lesson="Retry after changing the method.",
                tags=["parser", "retry"],
            )
        )
        self.journal.append_lesson(
            self.journal.build_lesson_entry(
                task_id="task-2",
                task_type="coding",
                lesson="Keep docs concise.",
                tags=["docs"],
            )
        )

        lessons = self.journal.read_relevant_lessons(tags=["retry"])

        self.assertEqual(len(lessons), 1)
        self.assertIn("retry", lessons[0]["tags"])

    def test_limit_prevents_full_return(self) -> None:
        for index in range(4):
            self.journal.append_lesson(
                self.journal.build_lesson_entry(
                    task_id=f"task-{index}",
                    task_type="coding",
                    lesson=f"Lesson {index}",
                )
            )

        lessons = self.journal.read_relevant_lessons(task_type="coding", limit=2)

        self.assertEqual(len(lessons), 2)

    def test_success_and_failure_paths_can_generate_lessons(self) -> None:
        success = self.journal.build_lesson_entry(
            task_id="task-success",
            task_type="coding",
            execution_result={
                "status": "success",
                "tool_name": "read_file",
                "output": {"summary": "ok"},
                "error": None,
                "artifacts": [],
                "metadata": {},
            },
        )
        failure = self.journal.build_lesson_entry(
            task_id="task-failure",
            task_type="coding",
            execution_result={
                "status": "error",
                "tool_name": "run_command",
                "output": None,
                "error": {"type": "execution_error", "message": "boom"},
                "artifacts": [],
                "metadata": {},
            },
        )

        self.assertEqual(success["source"], "success")
        self.assertEqual(failure["source"], "failure")
        self.assertNotEqual(success["lesson"], failure["lesson"])

    def test_lesson_structure_is_complete(self) -> None:
        entry = self.journal.build_lesson_entry(task_id="task-1", task_type="research", lesson="Verify source quality.")

        self.assertEqual(
            sorted(entry.keys()),
            sorted(
                [
                    "entry_id",
                    "task_id",
                    "task_type",
                    "tags",
                    "lesson",
                    "source",
                    "confidence",
                    "created_at",
                ]
            ),
        )

    def test_journal_is_not_task_block_or_distilled_summary_dump(self) -> None:
        entry = self.journal.build_lesson_entry(
            task_id="task-1",
            task_type="coding",
            lesson="Keep the parser patch narrow.",
        )

        self.assertNotIn("current_goal", entry)
        self.assertNotIn("distilled_summary", entry)
        self.assertNotIn("blockers", entry)

    def test_orchestrator_writes_minimal_lesson_after_run(self) -> None:
        storage_dir = self.temp_dir / "state"
        state_manager = StateManager(storage_dir)
        contract = self.builder.build("Implement parser safeguards for the harness.")
        state_manager.save_task_block(TaskBlock(task_id=contract.task_id, current_goal=contract.goal))

        result = Orchestrator().run(
            contract,
            state_manager,
            ContextEngine(),
            None,
            ToolDiscoveryService(),
            Executor(),
            verifier=Verifier(),
            learning_journal=self.journal,
        )

        self.assertEqual(result["learning_journal"]["status"], "written")
        self.assertTrue(result["learning_journal"]["written_entry_id"])
        stored = self.journal.read_relevant_lessons(task_type=contract.task_type.value)
        self.assertGreaterEqual(len(stored), 1)

    def test_next_run_reads_small_number_of_relevant_lessons_without_dominating_context(self) -> None:
        state_manager = StateManager(self.temp_dir / "state-second")
        contract = self.builder.build("Implement parser safeguards for the harness.")
        state_manager.save_task_block(TaskBlock(task_id=contract.task_id, current_goal=contract.goal))

        for index in range(3):
            self.journal.append_lesson(
                self.journal.build_lesson_entry(
                    task_id=f"task-seed-{index}",
                    task_type=contract.task_type.value,
                    lesson=f"Reusable coding lesson {index}",
                    tags=["parser"],
                )
            )

        result = Orchestrator().run(
            contract,
            state_manager,
            ContextEngine(),
            None,
            ToolDiscoveryService(),
            Executor(),
            learning_journal=self.journal,
        )

        self.assertEqual(result["learning_journal"]["read_count"], 2)
        self.assertLessEqual(result["working_context_summary"]["retrieval_packet_count"], 2)
        self.assertGreaterEqual(result["working_context_summary"]["task_note_count"], 1)


if __name__ == "__main__":
    unittest.main()
