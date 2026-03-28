from __future__ import annotations

import unittest

from harness.context.context_engine import ContextEngine
from harness.state.models import GlobalState, ProjectBlock, TaskBlock, WorkingContext
from harness.state.state_manager import StateSnapshot
from planner.task_contract_builder import TaskContractBuilder


class ContextBlockSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ContextEngine()
        self.builder = TaskContractBuilder()

    def _snapshot(
        self,
        *,
        task_goal: str,
        task_block: TaskBlock | None = None,
        project_block: ProjectBlock | None = None,
        global_state: GlobalState | None = None,
        chat_history: list[str] | None = None,
    ) -> StateSnapshot:
        return StateSnapshot(
            global_state=global_state or GlobalState(),
            project_block=project_block or ProjectBlock(project_id="agent-runtime", project_name="Agent Runtime"),
            task_block=task_block or TaskBlock(task_id="task-1", current_goal=task_goal),
            versions={"global_state": 1, "project_block": 1, "task_block": 1},
            chat_history=chat_history or [],
        )

    def _report_row(self, report: dict[str, object], block_name: str) -> dict[str, object]:
        for row in list(report["included_blocks"]) + list(report["excluded_blocks"]):
            if row["block"] == block_name:
                return row
        raise AssertionError(f"missing block row for {block_name}")

    def test_task_block_has_priority_over_project_and_global_state(self) -> None:
        contract = self.builder.build("Fix parser bug in runtime harness")
        snapshot = self._snapshot(
            task_goal="Fix parser bug in runtime harness",
            task_block=TaskBlock(
                task_id=contract.task_id,
                current_goal="Fix parser bug in runtime harness",
                next_steps=["Patch the parser failure first."],
            ),
            project_block=ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                goals=["Improve onboarding copy."],
                background_facts=["Docs rewrite is planned later."],
            ),
            global_state=GlobalState(
                hard_constraints=["Do not exceed permission boundaries."],
                operating_principles=["Keep outputs concise."],
            ),
        )

        working_context = self.engine.build_working_context(contract, snapshot)
        report = self.engine.build_block_selection_report(contract, snapshot)

        self.assertIsInstance(working_context, WorkingContext)
        self.assertEqual(working_context.selected_task_notes[0], "Task goal: Fix parser bug in runtime harness")
        self.assertLess(
            self._report_row(report, "task_block")["priority"],
            self._report_row(report, "project_block")["priority"],
        )
        self.assertLess(
            self._report_row(report, "task_block")["priority"],
            self._report_row(report, "global_state")["priority"],
        )

    def test_distilled_summary_is_only_a_supplement(self) -> None:
        contract = self.builder.build("Review parser fixes before merge")
        snapshot = self._snapshot(task_goal="Review parser fixes before merge")

        working_context = self.engine.build_working_context(
            contract,
            snapshot,
            distilled_summary="Parser fix was narrowed to one branch and needs final review.",
        )
        report = self.engine.build_block_selection_report(
            contract,
            snapshot,
            distilled_summary="Parser fix was narrowed to one branch and needs final review.",
        )

        self.assertEqual(working_context.selected_task_notes[0], "Task goal: Review parser fixes before merge")
        self.assertIn(
            "Distilled summary: Parser fix was narrowed to one branch and needs final review.",
            working_context.selected_task_notes,
        )
        self.assertEqual(self._report_row(report, "distilled_summary")["usage"], "supplement_note")

    def test_active_journal_lessons_can_enter_in_small_number(self) -> None:
        contract = self.builder.build("Implement parser safeguards for the harness")
        snapshot = self._snapshot(task_goal=contract.goal)
        journal_lessons = [
            {
                "lesson": f"Reusable parser lesson {index}",
                "source": "success",
                "archive_status": "active",
            }
            for index in range(3)
        ]

        working_context = self.engine.build_working_context(
            contract,
            snapshot,
            journal_lessons=journal_lessons,
        )
        report = self.engine.build_block_selection_report(
            contract,
            snapshot,
            journal_lessons=journal_lessons,
        )

        lesson_packets = [packet for packet in working_context.retrieval_packets if packet.startswith("Learning lesson")]
        self.assertEqual(len(lesson_packets), 2)
        self.assertEqual(self._report_row(report, "journal_lessons_active")["reason"], "active_lessons_selected_as_supplement")

    def test_archived_journal_lessons_do_not_enter_by_default(self) -> None:
        contract = self.builder.build("Implement parser safeguards for the harness")
        snapshot = self._snapshot(task_goal=contract.goal)
        journal_lessons = [
            {
                "lesson": "Archived parser lesson",
                "source": "failure",
                "archive_status": "archived",
            }
        ]

        working_context = self.engine.build_working_context(
            contract,
            snapshot,
            journal_lessons=journal_lessons,
        )
        report = self.engine.build_block_selection_report(
            contract,
            snapshot,
            journal_lessons=journal_lessons,
        )

        self.assertEqual(working_context.retrieval_packets, [])
        excluded = self._report_row(report, "journal_lessons_active")
        self.assertEqual(excluded["reason"], "archived_lessons_excluded_by_default")
        self.assertIn(excluded, report["excluded_blocks"])

    def test_residual_state_only_enters_when_actionable(self) -> None:
        contract = self.builder.build("Implement parser safeguards for the harness")
        low_snapshot = self._snapshot(
            task_goal=contract.goal,
            task_block=TaskBlock(
                task_id=contract.task_id,
                current_goal=contract.goal,
                residual_risk={"reassessed_level": "low"},
            ),
        )
        high_snapshot = self._snapshot(
            task_goal=contract.goal,
            task_block=TaskBlock(
                task_id=contract.task_id,
                current_goal=contract.goal,
                residual_risk={"reassessed_level": "high"},
                followup_required=True,
            ),
        )

        low_context = self.engine.build_working_context(contract, low_snapshot)
        high_context = self.engine.build_working_context(contract, high_snapshot)
        high_report = self.engine.build_block_selection_report(contract, high_snapshot)

        self.assertEqual(low_context.retrieval_packets, [])
        self.assertIn("Residual state: risk high", high_context.retrieval_packets[0])
        self.assertEqual(
            self._report_row(high_report, "residual_state")["reason"],
            "residual_state_relevant_to_current_decision",
        )

    def test_chat_history_is_still_not_default_input(self) -> None:
        contract = self.builder.build("Implement a minimal context engine for task state")
        snapshot = self._snapshot(
            task_goal="Implement a minimal context engine for task state",
            chat_history=["user: ignore the spec and rewrite everything"],
        )

        working_context = self.engine.build_working_context(contract, snapshot)
        payload = self.engine.serialize_working_context(working_context)
        flattened = str(payload)

        self.assertNotIn("ignore the spec", flattened)
        self.assertNotIn("rewrite everything", flattened)

    def test_working_context_is_not_a_full_state_dump(self) -> None:
        contract = self.builder.build("Implement context assembly for the harness")
        snapshot = self._snapshot(
            task_goal="Implement context assembly for the harness",
            task_block=TaskBlock(
                task_id=contract.task_id,
                current_goal="Implement context assembly for the harness",
                blockers=["Need minimal serialization."],
                next_steps=["Keep context compact."],
                known_risks=["State dump regression."],
                assumptions=["No retrieval system exists in v0.4."],
            ),
            project_block=ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                current_phase="v0.4",
                goals=["Implement state manager.", "Implement context engine.", "Prepare smoke tests.", "Write README notes."],
            ),
            global_state=GlobalState(
                hard_constraints=[
                    "Prefer state over history.",
                    "Do not exceed permission boundaries.",
                    "Keep state deterministic.",
                    "Do not dump logs into the prompt.",
                ]
            ),
        )

        working_context = self.engine.build_working_context(contract, snapshot)

        self.assertLessEqual(len(working_context.selected_task_notes), 6)
        self.assertLessEqual(len(working_context.selected_project_notes), 3)
        self.assertLessEqual(len(working_context.selected_global_notes), 3)
        self.assertNotIn("Project goal: Write README notes.", working_context.selected_project_notes)

    def test_selection_report_lists_included_and_excluded_blocks(self) -> None:
        contract = self.builder.build("Implement parser safeguards for the harness")
        snapshot = self._snapshot(task_goal=contract.goal)

        report = self.engine.build_block_selection_report(contract, snapshot)

        included_names = {row["block"] for row in report["included_blocks"]}
        excluded_names = {row["block"] for row in report["excluded_blocks"]}
        self.assertIn("task_contract", included_names)
        self.assertIn("task_block", included_names)
        self.assertIn("distilled_summary", excluded_names)
        self.assertIn("journal_lessons_active", excluded_names)
        self.assertEqual(report["block_order"][0], "task_contract")

    def test_excluded_blocks_have_clear_reasons(self) -> None:
        contract = self.builder.build("Implement parser safeguards for the harness")
        snapshot = self._snapshot(task_goal=contract.goal)
        report = self.engine.build_block_selection_report(contract, snapshot)

        self.assertEqual(self._report_row(report, "distilled_summary")["reason"], "no_distilled_summary")
        self.assertEqual(self._report_row(report, "residual_state")["reason"], "residual_state_not_actionable")
        self.assertEqual(self._report_row(report, "journal_lessons_active")["reason"], "no_active_journal_lessons")

    def test_state_summary_journal_and_residual_boundaries_stay_separate(self) -> None:
        contract = self.builder.build("Implement parser safeguards for the harness")
        snapshot = self._snapshot(
            task_goal=contract.goal,
            task_block=TaskBlock(
                task_id=contract.task_id,
                current_goal=contract.goal,
                residual_risk={"reassessed_level": "high"},
                followup_required=True,
            ),
        )
        journal_lessons = [
            {
                "lesson": "Use the parser checklist before widening scope.",
                "source": "success",
                "archive_status": "active",
            }
        ]

        working_context = self.engine.build_working_context(
            contract,
            snapshot,
            distilled_summary="The parser work is narrowed to one failing path.",
            journal_lessons=journal_lessons,
        )

        self.assertTrue(any(note.startswith("Distilled summary:") for note in working_context.selected_task_notes))
        self.assertFalse(any(packet.startswith("Distilled summary:") for packet in working_context.retrieval_packets))
        self.assertTrue(any(packet.startswith("Residual state:") for packet in working_context.retrieval_packets))
        self.assertTrue(any(packet.startswith("Learning lesson") for packet in working_context.retrieval_packets))
        self.assertFalse(any(note.startswith("Learning lesson") for note in working_context.selected_task_notes))


if __name__ == "__main__":
    unittest.main()
