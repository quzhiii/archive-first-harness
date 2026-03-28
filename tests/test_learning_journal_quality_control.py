from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest

from harness.context.context_engine import ContextEngine
from harness.journal.learning_journal import LearningJournal
from harness.state.models import GlobalState, ProjectBlock, TaskBlock
from harness.state.state_manager import StateSnapshot
from planner.task_contract_builder import TaskContractBuilder


class LearningJournalQualityControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_learning_journal_qc_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.store_path = self.temp_dir / "learning_journal.jsonl"
        self.journal = LearningJournal(self.store_path)
        self.builder = TaskContractBuilder()
        self.context_engine = ContextEngine()

    def _build_entry(
        self,
        *,
        task_id: str,
        task_type: str = "coding",
        lesson: str = "Keep parser fixes scoped to the failing module.",
        tags: list[str] | None = None,
    ) -> dict[str, object]:
        return self.journal.build_lesson_entry(
            task_id=task_id,
            task_type=task_type,
            lesson=lesson,
            tags=tags,
        )

    def test_active_and_archived_layers_are_distinct(self) -> None:
        appended = self.journal.append_lesson(self._build_entry(task_id="task-1"))
        archived = self.journal.archive_entry(str(appended["entry_id"]))

        self.assertEqual(archived["archive_status"], "archived")
        self.assertEqual(archived["archive_reason"], "manual")
        self.assertEqual(self.journal.read_relevant_lessons(task_type="coding", limit=10), [])

        with_archived = self.journal.read_relevant_lessons(
            task_type="coding",
            limit=10,
            include_archived=True,
        )
        self.assertEqual(len(with_archived), 1)
        self.assertEqual(with_archived[0]["archive_status"], "archived")

    def test_duplicate_lessons_do_not_accumulate_without_bound(self) -> None:
        first = self.journal.append_lesson(
            self._build_entry(
                task_id="task-1",
                lesson="Keep runtime parser fixes scoped to the failing branch.",
                tags=["parser", "scope"],
            )
        )
        duplicate = self.journal.append_lesson(
            self._build_entry(
                task_id="task-2",
                lesson="Keep runtime parser fixes scoped to the failing branch.",
                tags=["scope", "parser"],
            )
        )

        self.assertEqual(first["entry_id"], duplicate["entry_id"])
        self.assertEqual(len(self.store_path.read_text(encoding="utf-8").splitlines()), 1)
        stored = self.journal.read_relevant_lessons(task_type="coding", limit=10)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["task_id"], "task-2")

    def test_expired_lessons_are_archived_not_deleted(self) -> None:
        entry = self._build_entry(task_id="task-expired")
        entry["created_at"] = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        entry["ttl_days"] = 1
        self.journal.append_lesson(entry)

        self.assertEqual(self.journal.read_relevant_lessons(task_type="coding", limit=10), [])
        with_archived = self.journal.read_relevant_lessons(
            task_type="coding",
            limit=10,
            include_archived=True,
        )
        self.assertEqual(len(with_archived), 1)
        self.assertEqual(with_archived[0]["archive_status"], "archived")
        self.assertEqual(with_archived[0]["archive_reason"], "expired")

    def test_default_reads_only_active_entries(self) -> None:
        active = self._build_entry(task_id="task-active", lesson="Keep success criteria explicit.")
        archived = self._build_entry(task_id="task-archived", lesson="Old parser note.")
        archived["created_at"] = (datetime.now(UTC) - timedelta(days=20)).isoformat()
        archived["ttl_days"] = 1

        self.journal.append_lesson(active)
        self.journal.append_lesson(archived)

        active_only = self.journal.read_relevant_lessons(task_type="coding", limit=10)
        self.assertEqual(len(active_only), 1)
        self.assertEqual(active_only[0]["task_id"], "task-active")
        self.assertEqual(active_only[0]["archive_status"], "active")

    def test_include_archived_can_return_archived_entries_explicitly(self) -> None:
        active = self._build_entry(task_id="task-active", lesson="Active parser note.")
        archived = self._build_entry(task_id="task-archived", lesson="Archived parser note.")
        archived["created_at"] = (datetime.now(UTC) - timedelta(days=20)).isoformat()
        archived["ttl_days"] = 1

        self.journal.append_lesson(active)
        self.journal.append_lesson(archived)

        all_entries = self.journal.read_relevant_lessons(
            task_type="coding",
            limit=10,
            include_archived=True,
        )
        self.assertEqual(len(all_entries), 2)
        self.assertEqual({entry["archive_status"] for entry in all_entries}, {"active", "archived"})

    def test_high_confidence_unexpired_unique_lesson_stays_active(self) -> None:
        entry = self._build_entry(
            task_id="task-strong",
            lesson="Keep codegen patches scoped and reviewed before widening impact.",
        )
        entry["confidence"] = 0.95
        entry["ttl_days"] = 45

        appended = self.journal.append_lesson(entry)

        self.assertEqual(appended["archive_status"], "active")
        self.assertIsNone(appended["archive_reason"])
        self.assertEqual(len(self.journal.read_relevant_lessons(task_type="coding", limit=10)), 1)

    def test_residual_or_sandbox_payloads_are_not_mirrored_into_journal_body(self) -> None:
        entry = self.journal.build_lesson_entry(
            task_id="task-boundary",
            task_type="coding",
            execution_result={
                "status": "error",
                "tool_name": "write_file",
                "output": None,
                "error": {"type": "execution_error", "message": "boom"},
                "artifacts": [],
                "metadata": {"tool_input": {"path": "artifacts/output.txt"}},
            },
            residual_snapshot={
                "residual_risk": {"reassessed_level": "high"},
                "followup_required": True,
                "governance_required": True,
                "state_writeback_payload": {"task_id": "should-not-copy"},
            },
            sandbox_result={
                "status": "error",
                "snapshot_ref": "snapshot-1",
                "output": {"execution_result": {"status": "error"}},
            },
            rollback_result={
                "status": "rolled_back",
                "restored_state": {"task_id": "should-not-copy"},
            },
        )
        stored = self.journal.append_lesson(entry)
        serialized = str(stored)

        self.assertNotIn("state_writeback_payload", stored)
        self.assertNotIn("sandbox_result", stored)
        self.assertNotIn("rollback_result", stored)
        self.assertNotIn("snapshot_ref", serialized)
        self.assertNotIn("restored_state", serialized)

    def test_archived_lessons_do_not_dominate_working_context(self) -> None:
        contract = self.builder.build("Implement parser safeguards for the harness.")
        active = self._build_entry(
            task_id="task-active-context",
            task_type=contract.task_type.value,
            lesson="Use the active parser fix checklist.",
            tags=["active"],
        )
        archived = self._build_entry(
            task_id="task-archived-context",
            task_type=contract.task_type.value,
            lesson="Old archived parser heuristic.",
            tags=["archived"],
        )
        archived["created_at"] = (datetime.now(UTC) - timedelta(days=20)).isoformat()
        archived["ttl_days"] = 1

        self.journal.append_lesson(active)
        self.journal.append_lesson(archived)

        snapshot = StateSnapshot(
            global_state=GlobalState(),
            project_block=ProjectBlock(project_id="agent-runtime", project_name="Agent Runtime"),
            task_block=TaskBlock(task_id=contract.task_id, current_goal=contract.goal),
            versions={"global_state": 0, "project_block": 0, "task_block": 0},
        )
        working_context = self.context_engine.build_working_context(
            contract,
            snapshot,
            journal_lessons=self.journal.read_relevant_lessons(task_type=contract.task_type.value, limit=10),
        )
        packets = "\n".join(working_context.retrieval_packets)

        self.assertIn("Use the active parser fix checklist.", packets)
        self.assertNotIn("Old archived parser heuristic.", packets)
        self.assertLessEqual(len(working_context.retrieval_packets), 1)

    def test_existing_read_write_filters_and_limit_still_work(self) -> None:
        self.journal.append_lesson(
            self._build_entry(task_id="task-1", task_type="coding", lesson="Coding lesson", tags=["parser"])
        )
        self.journal.append_lesson(
            self._build_entry(task_id="task-2", task_type="research", lesson="Research lesson", tags=["docs"])
        )
        self.journal.append_lesson(
            self._build_entry(task_id="task-3", task_type="coding", lesson="Coding lesson two", tags=["retry"])
        )

        coding = self.journal.read_relevant_lessons(task_type="coding", limit=10)
        tagged = self.journal.read_relevant_lessons(tags=["retry"], limit=10)
        limited = self.journal.read_relevant_lessons(limit=1)

        self.assertEqual(len(coding), 2)
        self.assertEqual(len(tagged), 1)
        self.assertIn("retry", tagged[0]["tags"])
        self.assertEqual(len(limited), 1)


if __name__ == "__main__":
    unittest.main()
