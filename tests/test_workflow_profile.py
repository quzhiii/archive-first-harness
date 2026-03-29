from __future__ import annotations

import unittest

from harness.context.context_engine import ContextEngine
from harness.contracts.workflow_profile import (
    DEFAULT_WORKFLOW_PROFILE_ID,
    default_workflow_profile_id_for_task_type,
    resolve_workflow_profile,
)
from harness.evaluation.evaluation_input import build_evaluation_input_bundle
from harness.evaluation.realm_evaluator import RealmEvaluator
from harness.state.models import GlobalState, ProjectBlock, TaskBlock, TaskType
from harness.state.state_manager import StateSnapshot
from planner.task_contract_builder import TaskContractBuilder


class WorkflowProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = TaskContractBuilder()
        self.engine = ContextEngine()
        self.evaluator = RealmEvaluator()

    def _snapshot(self, *, contract, background_facts: list[str] | None = None) -> StateSnapshot:
        return StateSnapshot(
            global_state=GlobalState(
                hard_constraints=[
                    "Keep the runtime harness inside the approved contract boundary.",
                ]
            ),
            project_block=ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                background_facts=background_facts or [],
            ),
            task_block=TaskBlock(
                task_id=contract.task_id,
                contract_id=contract.contract_id,
                current_goal=contract.goal,
                next_steps=["Use the smallest useful context."],
            ),
            versions={"global_state": 1, "project_block": 1, "task_block": 1},
        )

    def test_default_profile_is_stable_when_not_explicitly_provided(self) -> None:
        contract = self.builder.build("Help.")

        self.assertEqual(contract.workflow_profile_id, DEFAULT_WORKFLOW_PROFILE_ID)
        self.assertEqual(
            default_workflow_profile_id_for_task_type(TaskType.GENERATION),
            DEFAULT_WORKFLOW_PROFILE_ID,
        )
        self.assertEqual(
            resolve_workflow_profile(contract.workflow_profile_id).profile_id,
            DEFAULT_WORKFLOW_PROFILE_ID,
        )

    def test_builtin_profiles_can_be_selected_or_inferred(self) -> None:
        research_contract = self.builder.build(
            "Analyze runtime harness evidence and summarize the result.",
            constraints={"workflow_profile_id": "research_analysis"},
        )
        review_contract = self.builder.build(
            "Review the runtime regression output.",
            constraints={"mission_profile_id": "evaluation_regression"},
        )
        coding_contract = self.builder.build("Implement a runtime harness patch.")

        self.assertEqual(research_contract.workflow_profile_id, "research_analysis")
        self.assertEqual(review_contract.workflow_profile_id, "evaluation_regression")
        self.assertEqual(coding_contract.workflow_profile_id, "implementation_build")
        self.assertEqual(
            default_workflow_profile_id_for_task_type(TaskType.PLANNING),
            "planning_design",
        )

    def test_task_contract_summary_carries_only_minimal_profile_fields(self) -> None:
        contract = self.builder.build(
            "Design a narrow roadmap for runtime hardening.",
            constraints={"workflow_profile_id": "planning_design"},
        )

        summary = build_evaluation_input_bundle(task_contract=contract).task_contract_summary

        self.assertEqual(summary["workflow_profile_id"], "planning_design")
        self.assertEqual(summary["intent_class"], "planning")
        self.assertIn("constraint coverage", summary["success_focus"])
        self.assertNotIn("context_bias", summary)
        self.assertNotIn("evaluation_bias", summary)
        self.assertNotIn("notes", summary)
        self.assertNotIn("workflow_profile", summary)

    def test_context_selection_bias_is_lightweight_and_keeps_boundaries(self) -> None:
        research_contract = self.builder.build(
            "Review parser runtime harness signals.",
            constraints={"workflow_profile_id": "research_analysis"},
        )
        build_contract = self.builder.build(
            "Review parser runtime harness signals.",
            constraints={"workflow_profile_id": "implementation_build"},
        )
        background_facts = [
            "Evidence signal for parser runtime harness changes.",
            "Execution safety signal for parser runtime harness changes.",
        ]
        journal_lessons = [
            {
                "lesson": "Evidence checklist for runtime parser analysis.",
                "source": "success",
                "tags": ["research", "evidence"],
                "archive_status": "active",
            },
            {
                "lesson": "Execution safety checklist for runtime parser patches.",
                "source": "followup",
                "tags": ["build", "safety"],
                "archive_status": "active",
            },
            {
                "lesson": "Archived scope note that should stay out.",
                "source": "failure",
                "tags": ["archived"],
                "archive_status": "archived",
            },
        ]

        research_context = self.engine.build_working_context(
            research_contract,
            self._snapshot(contract=research_contract, background_facts=background_facts),
            journal_lessons=journal_lessons,
        )
        build_context = self.engine.build_working_context(
            build_contract,
            self._snapshot(contract=build_contract, background_facts=background_facts),
            journal_lessons=journal_lessons,
        )

        self.assertIn("Evidence signal", research_context.selected_project_notes[0])
        self.assertIn("Execution safety signal", build_context.selected_project_notes[0])
        self.assertIn("Evidence checklist", research_context.retrieval_packets[0])
        self.assertIn("Execution safety checklist", build_context.retrieval_packets[0])
        self.assertFalse(
            any("Archived scope note" in packet for packet in research_context.retrieval_packets)
        )
        self.assertFalse(
            any("Archived scope note" in packet for packet in build_context.retrieval_packets)
        )
        self.assertLessEqual(len(research_context.retrieval_packets), 2)
        self.assertLessEqual(len(build_context.retrieval_packets), 2)

    def test_realm_evaluator_bias_changes_interpretation_not_control(self) -> None:
        default_contract = self.builder.build("Help.")
        regression_contract = self.builder.build(
            "Review the runtime regression result.",
            constraints={"workflow_profile_id": "evaluation_regression"},
        )
        metrics_summary = {
            "metrics": {
                "retry_count": {"last": 1},
                "skill_hit_rate": {"last": 1},
            }
        }

        default_result = self.evaluator.evaluate_bundle(
            build_evaluation_input_bundle(
                task_contract=default_contract,
                metrics_summary=metrics_summary,
            )
        )
        regression_result = self.evaluator.evaluate_bundle(
            build_evaluation_input_bundle(
                task_contract=regression_contract,
                metrics_summary=metrics_summary,
            )
        )

        self.assertEqual(default_result["recommendation"], "observe")
        self.assertEqual(regression_result["recommendation"], "observe")
        self.assertEqual(regression_result["metadata"]["automatic_action"], "none")
        self.assertEqual(
            regression_result["metadata"]["workflow_profile_id"],
            "evaluation_regression",
        )
        self.assertNotEqual(default_result["summary"], regression_result["summary"])
        self.assertIn("Evaluation Regression perspective", regression_result["summary"])

    def test_bundle_profile_surface_stays_small(self) -> None:
        contract = self.builder.build(
            "Review parser runtime harness signals.",
            constraints={"workflow_profile_id": "research_analysis"},
        )
        bundle = build_evaluation_input_bundle(task_contract=contract).as_dict()
        task_summary = bundle["task_contract_summary"]

        self.assertEqual(
            sorted([key for key in task_summary if key.startswith("workflow") or key in {"intent_class", "success_focus"}]),
            ["intent_class", "success_focus", "workflow_profile_id"],
        )
        self.assertNotIn("context_bias", str(bundle))
        self.assertNotIn("evaluation_bias", str(bundle))
        self.assertNotIn("notes", str(bundle))


if __name__ == "__main__":
    unittest.main()


