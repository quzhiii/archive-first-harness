from __future__ import annotations

import unittest

from planner.interviewer import Interviewer
from planner.task_contract_builder import TaskContractBuilder


class InterviewerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.interviewer = Interviewer()
        self.builder = TaskContractBuilder()

    def test_generates_clarification_questions_when_information_is_missing(self) -> None:
        result = self.interviewer.review("Help")

        self.assertTrue(result["should_continue"])
        self.assertGreater(len(result["questions"]), 0)
        self.assertIn("success_criteria", result["missing_fields"])
        self.assertIn("goal", result["missing_fields"])

    def test_stops_asking_when_minimum_information_is_present(self) -> None:
        result = self.interviewer.review(
            "Implement parser patch.",
            known_answers={
                "success_criteria": ["All parser tests pass."],
                "allowed_tools": ["read_files", "edit_files"],
                "write_permission_level": "write",
                "residual_risk_level": "low",
            },
        )

        self.assertFalse(result["should_continue"])
        self.assertEqual(result["questions"], [])
        self.assertTrue(result["stop_conditions_met"])
        self.assertEqual(result["stop_reason"], "minimum_information_satisfied")

    def test_question_count_is_capped(self) -> None:
        result = self.interviewer.review("This")

        self.assertLessEqual(len(result["questions"]), self.interviewer.MAX_QUESTIONS)

    def test_output_shape_is_clear(self) -> None:
        result = self.interviewer.review("Review the patch.", known_answers={"residual_risk_level": "low"})

        self.assertEqual(
            sorted(result.keys()),
            sorted(
                [
                    "should_continue",
                    "questions",
                    "missing_fields",
                    "stop_conditions_met",
                    "stop_reason",
                    "clarified_constraints",
                ]
            ),
        )

    def test_can_feed_clarified_constraints_into_task_contract_builder(self) -> None:
        interview_result = self.interviewer.review(
            "Implement parser patch.",
            known_answers={
                "task_id": "task-shared-1",
                "success_criteria": ["Parser unit tests pass."],
                "allowed_tools": ["read_files", "edit_files", "run_tests"],
                "write_permission_level": "write",
                "residual_risk_level": "low",
                "expected_artifacts": ["code_patch"],
            },
        )

        contract = self.builder.build_from_interview("Implement parser patch.", interview_result)

        self.assertEqual(contract.task_id, "task-shared-1")
        self.assertEqual(contract.success_criteria, ["Parser unit tests pass."])
        self.assertEqual(contract.allowed_tools, ["read_files", "edit_files", "run_tests"])
        self.assertEqual(contract.expected_artifacts, ["code_patch"])


if __name__ == "__main__":
    unittest.main()
