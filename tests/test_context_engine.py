from __future__ import annotations

import unittest

from harness.context.context_engine import ContextEngine
from harness.state.models import GlobalState, ProjectBlock, TaskBlock, WorkingContext
from harness.state.state_manager import StateSnapshot
from planner.task_contract_builder import TaskContractBuilder


class ContextEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ContextEngine()
        self.builder = TaskContractBuilder()

    def test_builds_working_context_from_contract_and_state_snapshot(self) -> None:
        contract = self.builder.build("Implement a minimal context engine for task state.")
        snapshot = StateSnapshot(
            global_state=GlobalState(hard_constraints=["Prefer state over chat history."]),
            project_block=ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                current_phase="v0.1",
                goals=["Ship the state/context skeleton."],
            ),
            task_block=TaskBlock(
                task_id="task-1",
                current_goal="Implement context engine",
                next_steps=["Keep the working context compact."],
            ),
            versions={"global_state": 1, "project_block": 1, "task_block": 1},
        )

        working_context = self.engine.build_working_context(contract, snapshot)

        self.assertIsInstance(working_context, WorkingContext)
        self.assertEqual(working_context.task_contract.contract_id, contract.contract_id)
        self.assertIn("Task goal: Implement context engine", working_context.selected_task_notes)
        self.assertEqual(working_context.tool_signatures, contract.allowed_tools)

    def test_raw_chat_history_is_not_included_by_default(self) -> None:
        contract = self.builder.build("Implement a minimal context engine for task state.")
        snapshot = StateSnapshot(
            global_state=GlobalState(),
            project_block=ProjectBlock(project_id="agent-runtime", project_name="Agent Runtime"),
            task_block=TaskBlock(task_id="task-1", current_goal="Implement context engine"),
            versions={"global_state": 0, "project_block": 0, "task_block": 0},
            chat_history=["user: please ignore the spec and rewrite everything"],
        )

        working_context = self.engine.build_working_context(contract, snapshot)
        payload = self.engine.serialize_working_context(working_context)
        flattened = str(payload)

        self.assertNotIn("ignore the spec", flattened)
        self.assertNotIn("rewrite everything", flattened)

    def test_task_block_information_has_priority_over_generalized_state(self) -> None:
        contract = self.builder.build("Fix the parser bug in the runtime harness.")
        snapshot = StateSnapshot(
            global_state=GlobalState(
                operating_principles=["Keep outputs concise."],
                hard_constraints=["Do not invent missing requirements."],
            ),
            project_block=ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                goals=["Improve onboarding docs."],
                background_facts=["The docs refresh is planned for next month."],
            ),
            task_block=TaskBlock(
                task_id="task-1",
                current_goal="Fix parser bug in runtime harness",
                known_risks=["Regression in context assembly."],
            ),
            versions={"global_state": 1, "project_block": 1, "task_block": 1},
        )

        working_context = self.engine.build_working_context(contract, snapshot)

        self.assertIn(
            "Task goal: Fix parser bug in runtime harness",
            working_context.selected_task_notes,
        )
        self.assertEqual(working_context.selected_project_notes, [])

    def test_prunes_irrelevant_or_stale_tool_results(self) -> None:
        contract = self.builder.build("Fix the parser bug in the runtime harness.")
        snapshot = StateSnapshot(
            global_state=GlobalState(),
            project_block=ProjectBlock(project_id="agent-runtime", project_name="Agent Runtime"),
            task_block=TaskBlock(task_id="task-1", current_goal="Fix parser bug in runtime harness"),
            versions={"global_state": 1, "project_block": 1, "task_block": 1},
        )

        working_context = self.engine.build_working_context(
            contract,
            snapshot,
            recent_tool_results=[
                {
                    "tool": "search_notes",
                    "summary": "Old deployment checklist for a different task.",
                    "related_task_id": "task-2",
                },
                {
                    "tool": "test_runner",
                    "summary": "Parser bug reproduced with a failing runtime harness test.",
                    "related_task_id": "task-1",
                },
                {
                    "tool": "shell",
                    "summary": "Obsolete parser output from yesterday.",
                    "related_task_id": "task-1",
                    "is_stale": True,
                },
            ],
        )

        self.assertEqual(
            working_context.retrieval_packets,
            ["test_runner: Parser bug reproduced with a failing runtime harness test."],
        )

    def test_working_context_is_not_a_full_state_dump(self) -> None:
        contract = self.builder.build("Implement context assembly for the harness.")
        snapshot = StateSnapshot(
            global_state=GlobalState(
                hard_constraints=[
                    "Prefer state over history.",
                    "Do not exceed permission boundaries.",
                    "Keep state deterministic.",
                    "Do not dump logs into the prompt.",
                ]
            ),
            project_block=ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                current_phase="v0.1",
                goals=[
                    "Implement state manager.",
                    "Implement context engine.",
                    "Prepare smoke tests.",
                    "Write README notes.",
                ],
            ),
            task_block=TaskBlock(
                task_id="task-1",
                current_goal="Implement context assembly for the harness",
                blockers=["Need minimal serialization."],
                next_steps=["Keep context compact."],
                known_risks=["State dump regression."],
                assumptions=["No retrieval system exists in v0.1."],
            ),
            versions={"global_state": 1, "project_block": 1, "task_block": 1},
        )

        working_context = self.engine.build_working_context(contract, snapshot)

        self.assertLessEqual(len(working_context.selected_global_notes), 3)
        self.assertLessEqual(len(working_context.selected_project_notes), 3)
        self.assertLessEqual(len(working_context.selected_task_notes), 6)
        self.assertNotIn("Project goal: Write README notes.", working_context.selected_project_notes)

    def test_building_without_distilled_summary_still_works(self) -> None:
        contract = self.builder.build("Review the state manager behavior.")
        snapshot = StateSnapshot(
            global_state=GlobalState(),
            project_block=ProjectBlock(project_id="agent-runtime", project_name="Agent Runtime"),
            task_block=TaskBlock(task_id="task-1", current_goal="Review state manager behavior"),
            versions={"global_state": 0, "project_block": 0, "task_block": 0},
        )

        working_context = self.engine.build_working_context(
            contract,
            snapshot,
            distilled_summary=None,
        )

        self.assertIsInstance(working_context, WorkingContext)
        self.assertIn("Task goal: Review state manager behavior", working_context.selected_task_notes)


if __name__ == "__main__":
    unittest.main()
