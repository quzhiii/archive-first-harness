from __future__ import annotations

import unittest

from harness.evaluation.profile_interpretation import build_profile_interpretation


class ProfileInterpretationTests(unittest.TestCase):
    def test_known_profile_returns_stable_focus_metadata(self) -> None:
        interpretation = build_profile_interpretation(
            "evaluation_regression",
            task_type="review",
            artifact_type="metrics_summary",
        )

        self.assertEqual(interpretation.workflow_profile_id, "evaluation_regression")
        self.assertEqual(interpretation.intent_class, "evaluation")
        self.assertEqual(list(interpretation.comparison_focus), ["baseline drift", "metrics stability"])
        self.assertEqual(list(interpretation.evaluation_focus), ["baseline drift", "metrics stability"])
        self.assertEqual(interpretation.artifact_relevance_hint, "primary")

    def test_missing_profile_uses_safe_task_type_default(self) -> None:
        interpretation = build_profile_interpretation(
            None,
            task_type="review",
            artifact_type="verification_report",
        )

        self.assertEqual(interpretation.workflow_profile_id, "evaluation_regression")
        self.assertEqual(interpretation.intent_class, "evaluation")

    def test_unknown_profile_falls_back_to_default_general(self) -> None:
        interpretation = build_profile_interpretation(
            "does_not_exist",
            task_type="review",
            artifact_type="event_trace",
        )

        self.assertEqual(interpretation.workflow_profile_id, "default_general")
        self.assertEqual(interpretation.intent_class, "general")
        self.assertEqual(list(interpretation.comparison_focus), ["baseline stability"])


if __name__ == "__main__":
    unittest.main()
