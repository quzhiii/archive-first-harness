from __future__ import annotations

import unittest

from harness.evaluation.realm_evaluator import RealmEvaluator


class RealmEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = RealmEvaluator()

    def test_outputs_structured_evaluation_from_minimal_metrics(self) -> None:
        metrics_summary = {
            "metrics": {
                "token_count": {"last": 200},
                "latency_ms": {"last": 100},
                "retry_count": {"last": 0},
                "rollback_count": {"last": 0},
                "context_size": {"last": 5},
                "skill_hit_rate": {"last": 1},
                "human_handoff_count": {"last": 0},
            }
        }

        result = self.evaluator.evaluate(metrics_summary)

        self.assertEqual(result["status"], "ok")
        self.assertIn("recommendation", result)
        self.assertIn("reason_codes", result)
        self.assertIn("summary", result)
        self.assertIn("requires_human_review", result)
        self.assertIn("metadata", result)

    def test_can_distinguish_keep_observe_and_retire_candidate(self) -> None:
        keep = self.evaluator.evaluate({"metrics": {"skill_hit_rate": {"last": 1}}})
        observe = self.evaluator.evaluate(
            {
                "metrics": {
                    "retry_count": {"last": 1},
                    "skill_hit_rate": {"last": 1},
                }
            }
        )
        retire_candidate = self.evaluator.evaluate(
            {
                "metrics": {
                    "retry_count": {"last": 4},
                    "rollback_count": {"last": 2},
                    "human_handoff_count": {"last": 1},
                    "skill_hit_rate": {"last": 0},
                }
            }
        )

        self.assertEqual(keep["recommendation"], "keep")
        self.assertEqual(observe["recommendation"], "observe")
        self.assertEqual(retire_candidate["recommendation"], "retire_candidate")

    def test_outputs_reason_codes(self) -> None:
        result = self.evaluator.evaluate(
            {
                "metrics": {
                    "latency_ms": {"last": 6000},
                    "skill_hit_rate": {"last": 1},
                }
            }
        )

        self.assertIn("high_latency", result["reason_codes"])

    def test_does_not_trigger_automatic_retirement(self) -> None:
        result = self.evaluator.evaluate(
            {
                "metrics": {
                    "retry_count": {"last": 4},
                    "rollback_count": {"last": 3},
                    "human_handoff_count": {"last": 1},
                    "skill_hit_rate": {"last": 0},
                }
            }
        )

        self.assertEqual(result["metadata"]["automatic_action"], "none")
        self.assertTrue(result["requires_human_review"])

    def test_unknown_profile_falls_back_without_changing_action_semantics(self) -> None:
        result = self.evaluator.evaluate(
            {
                "workflow_profile_id": "unknown_profile",
                "task_type": "review",
                "metrics": {
                    "retry_count": {"last": 1},
                    "skill_hit_rate": {"last": 1},
                },
            }
        )

        self.assertEqual(result["recommendation"], "observe")
        self.assertEqual(result["metadata"]["workflow_profile_id"], "default_general")
        self.assertEqual(result["metadata"]["automatic_action"], "none")

    def test_output_shape_is_complete(self) -> None:
        result = self.evaluator.evaluate({"metrics": {}})

        self.assertEqual(
            sorted(result.keys()),
            sorted(
                [
                    "status",
                    "recommendation",
                    "reason_codes",
                    "summary",
                    "requires_human_review",
                    "metadata",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
