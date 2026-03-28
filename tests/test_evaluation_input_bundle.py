from __future__ import annotations

import unittest

from harness.context.context_engine import ContextEngine
from harness.evaluation.baseline_compare import BaselineComparator
from harness.evaluation.evaluation_input import (
    EvaluationInputBundle,
    build_evaluation_input_bundle,
    summarize_event_trace,
    summarize_journal_append_trace,
    to_baseline_artifacts,
)
from harness.evaluation.realm_evaluator import RealmEvaluator
from harness.state.models import GlobalState, ProjectBlock, RiskLevel, TaskBlock, TaskContract, TaskType, WritePermissionLevel
from harness.state.state_manager import StateSnapshot


class EvaluationInputBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context_engine = ContextEngine()
        self.comparator = BaselineComparator()
        self.realm_evaluator = RealmEvaluator()
        self.task_contract = TaskContract(
            task_id="task-eval-1",
            contract_id="contract-eval-1",
            goal="Review retrieval evidence and produce a compact answer.",
            success_criteria=[
                "Return a grounded answer.",
                "Keep the answer within the approved scope.",
            ],
            allowed_tools=["search_docs", "read_file"],
            stop_conditions=["Stop if evidence quality drops below the required bar."],
            expected_artifacts=["answer"],
            task_type=TaskType.RETRIEVAL,
            write_permission_level=WritePermissionLevel.READ,
            residual_risk_level=RiskLevel.LOW,
            methodology_family="research",
        )
        self.state_snapshot = StateSnapshot(
            global_state=GlobalState(hard_constraints=["Do not widen scope without evidence."]),
            project_block=ProjectBlock(
                project_id="agent-runtime",
                project_name="Agent Runtime",
                current_phase="v0.4",
                goals=["Keep evaluation inputs comparable."],
            ),
            task_block=TaskBlock(
                task_id=self.task_contract.task_id,
                contract_id=self.task_contract.contract_id,
                current_goal=self.task_contract.goal,
                next_steps=["Inspect the evidence first."],
            ),
            versions={"global_state": 1, "project_block": 1, "task_block": 1},
        )
        self.block_selection_report = self.context_engine.build_block_selection_report(
            self.task_contract,
            self.state_snapshot,
            distilled_summary="The task is narrowed to one retrieval answer.",
            journal_lessons=[
                {
                    "lesson": "Keep retrieval scope narrow when evidence is partial.",
                    "source": "success",
                    "archive_status": "active",
                },
                {
                    "lesson": "Archived lesson should stay out of working context.",
                    "source": "failure",
                    "archive_status": "archived",
                },
            ],
        )
        self.verification_report = {
            "status": "passed",
            "passed": True,
            "issues": [],
            "warnings": [],
            "residual_risk_hint": "low",
        }
        self.residual_followup = {
            "status": "ok",
            "reassessment": {
                "reassessed_level": "low",
                "needs_followup": False,
            },
            "telemetry_payload": {
                "followup_required": False,
                "governance_required": False,
            },
            "governance": {
                "status": "clear",
                "requires_governance_override": False,
                "issues": [],
            },
            "auto_execution": "none",
        }
        self.metrics_summary = {
            "event_count": 2,
            "metric_count": 5,
            "metrics": {
                "retry_count": {"last": 0, "count": 1},
                "rollback_count": {"last": 0, "count": 1},
                "human_handoff_count": {"last": 0, "count": 1},
                "tool_misuse_count": {"last": 0, "count": 1},
                "skill_hit_rate": {"last": 1, "count": 1},
            },
        }
        self.event_trace = {
            "dispatch_trace": [
                {
                    "event_name": "on_verification_report",
                    "event_id": "evt-1",
                    "status": "success",
                    "handler_count": 0,
                    "timestamp": "2026-03-28T09:00:00+00:00",
                },
                {
                    "event_name": "on_journal_append",
                    "event_id": "evt-2",
                    "status": "success",
                    "handler_count": 1,
                    "timestamp": "2026-03-28T09:00:01+00:00",
                },
            ],
            "execution_status": "success",
        }
        self.journal_append_trace = {
            "dispatch_trace": [
                {
                    "event_name": "on_journal_append",
                    "event_id": "evt-2",
                    "status": "success",
                    "handler_count": 1,
                    "timestamp": "2026-03-28T09:00:01+00:00",
                }
            ],
            "payload": {
                "event_id": "evt-2",
                "timestamp": "2026-03-28T09:00:01+00:00",
                "task_id": self.task_contract.task_id,
                "contract_id": self.task_contract.contract_id,
                "schema_version": "v0.3",
                "lesson_entry": {
                    "entry_id": "lesson-1",
                    "task_id": self.task_contract.task_id,
                    "task_type": self.task_contract.task_type.value,
                    "tags": ["retrieval", "success"],
                    "lesson": "Keep retrieval scope narrow.",
                    "source": "success",
                    "confidence": 0.65,
                    "created_at": "2026-03-28T09:00:01+00:00",
                },
                "source": "success",
            },
            "journal_entry": {
                "entry_id": "lesson-1",
                "task_id": self.task_contract.task_id,
                "task_type": self.task_contract.task_type.value,
                "tags": ["retrieval", "success"],
                "lesson": "Keep retrieval scope narrow.",
                "source": "success",
                "confidence": 0.65,
                "created_at": "2026-03-28T09:00:01+00:00",
            },
            "learning_journal": {
                "status": "written",
                "written_entry_id": "lesson-1",
                "written_source": "success",
            },
        }

    def test_bundle_builds_expected_fields(self) -> None:
        bundle = build_evaluation_input_bundle(
            task_contract=self.task_contract,
            block_selection_report=self.block_selection_report,
            verification_report=self.verification_report,
            residual_followup=self.residual_followup,
            metrics_summary=self.metrics_summary,
            event_trace=self.event_trace,
            journal_append_trace=self.journal_append_trace,
        )

        self.assertIsInstance(bundle, EvaluationInputBundle)
        payload = bundle.as_dict()
        self.assertEqual(
            sorted(payload.keys()),
            sorted(
                [
                    "task_contract_summary",
                    "block_selection_report",
                    "verification_report",
                    "residual_followup",
                    "metrics_summary",
                    "event_trace_summary",
                    "journal_append_summary",
                ]
            ),
        )
        self.assertEqual(payload["task_contract_summary"]["task_id"], self.task_contract.task_id)
        self.assertEqual(payload["event_trace_summary"]["event_count"], 2)
        self.assertTrue(payload["journal_append_summary"]["append_happened"])

    def test_bundle_tolerates_missing_optional_inputs(self) -> None:
        bundle = build_evaluation_input_bundle(task_contract=self.task_contract)

        self.assertEqual(bundle.block_selection_report["included_blocks"], [])
        self.assertIsNone(bundle.verification_report)
        self.assertIsNone(bundle.residual_followup)
        self.assertIsNone(bundle.metrics_summary)
        self.assertEqual(bundle.event_trace_summary["event_count"], 0)
        self.assertFalse(bundle.journal_append_summary["append_happened"])

    def test_event_trace_summary_is_stable_and_minimal(self) -> None:
        trace = {
            "dispatch_trace": [
                {
                    "event_name": "on_verification_report",
                    "status": "success",
                    "timestamp": "2026-03-28T09:00:00+00:00",
                    "payload": {"large": "object"},
                },
                {
                    "event_name": "on_governance_check",
                    "status": "error",
                    "timestamp": "2026-03-28T09:00:01+00:00",
                    "error": {"type": "policy_conflict"},
                },
            ]
        }

        summary = summarize_event_trace(trace)

        self.assertEqual(summary["event_sequence"], ["on_verification_report", "on_governance_check"])
        self.assertEqual(summary["event_types"], ["on_verification_report", "on_governance_check"])
        self.assertTrue(summary["key_events"]["on_verification_report"])
        self.assertTrue(summary["key_events"]["on_governance_check"])
        self.assertEqual(summary["error_count"], 1)
        self.assertNotIn("dispatch_trace", summary)
        self.assertNotIn("payload", summary)

    def test_journal_append_summary_stays_small_and_reports_bloat(self) -> None:
        trace = dict(self.journal_append_trace)
        trace["journal_entry"] = dict(self.journal_append_trace["journal_entry"])
        trace["journal_entry"]["sandbox_result"] = {
            "status": "error",
            "snapshot_ref": "snapshot-1",
        }

        summary = summarize_journal_append_trace(trace)

        self.assertTrue(summary["append_happened"])
        self.assertEqual(summary["append_count"], 1)
        self.assertIn("success", summary["sources"])
        self.assertIn("retrieval", summary["tags"])
        self.assertIn("medium", summary["confidence_bands"])
        self.assertIn("journal_entry.sandbox_result", summary["forbidden_mirrored_fields"])
        self.assertNotIn("journal_entry", summary)
        self.assertNotIn("learning_journal", summary)

    def test_block_selection_report_is_carried_into_bundle(self) -> None:
        bundle = build_evaluation_input_bundle(
            task_contract=self.task_contract,
            block_selection_report=self.block_selection_report,
        )

        included_names = {row["block"] for row in bundle.block_selection_report["included_blocks"]}
        excluded_names = {row["block"] for row in bundle.block_selection_report["excluded_blocks"]}
        self.assertIn("task_contract", included_names)
        self.assertIn("journal_lessons_active", included_names)
        self.assertIn("residual_state", excluded_names)

    def test_bundle_can_export_baseline_compare_artifacts(self) -> None:
        bundle = build_evaluation_input_bundle(
            task_contract=self.task_contract,
            block_selection_report=self.block_selection_report,
            verification_report=self.verification_report,
            residual_followup=self.residual_followup,
            metrics_summary=self.metrics_summary,
            event_trace=self.event_trace,
            journal_append_trace=self.journal_append_trace,
        )

        artifacts = to_baseline_artifacts(bundle)
        verification_diff = self.comparator.compare_bundle_artifact(
            bundle,
            self.verification_report,
            artifact_type="verification_report",
        )
        event_diff = self.comparator.compare(
            artifacts["event_trace"],
            self.event_trace,
            artifact_type="event_trace",
        )
        journal_diff = self.comparator.compare(
            artifacts["journal_append_trace"],
            self.journal_append_trace,
            artifact_type="journal_append_trace",
        )

        self.assertEqual(artifacts["event_trace"]["dispatch_trace"][0]["event_name"], "on_verification_report")
        self.assertEqual(verification_diff["status"], "compatible")
        self.assertEqual(event_diff["status"], "compatible")
        self.assertEqual(journal_diff["status"], "compatible")

    def test_realm_evaluator_can_consume_bundle_without_new_semantics(self) -> None:
        bundle = build_evaluation_input_bundle(
            task_contract=self.task_contract,
            metrics_summary=self.metrics_summary,
        )

        direct = self.realm_evaluator.evaluate(self.metrics_summary)
        from_bundle = self.realm_evaluator.evaluate_bundle(bundle)

        self.assertEqual(from_bundle["recommendation"], direct["recommendation"])
        self.assertEqual(from_bundle["reason_codes"], direct["reason_codes"])
        self.assertEqual(from_bundle["metadata"]["automatic_action"], "none")

    def test_task_contract_summary_does_not_mirror_full_contract(self) -> None:
        bundle = build_evaluation_input_bundle(
            task_contract=self.task_contract,
            journal_append_trace=self.journal_append_trace,
        )

        task_summary = bundle.task_contract_summary
        journal_summary = bundle.journal_append_summary

        self.assertNotIn("allowed_tools", task_summary)
        self.assertNotIn("failure_escalation_policy", task_summary)
        self.assertNotIn("stop_conditions", journal_summary)
        self.assertNotIn("dispatch_trace", journal_summary)
        self.assertNotIn("entries", journal_summary)


if __name__ == "__main__":
    unittest.main()

