from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import json
import unittest

from harness.evaluation.baseline_compare import BaselineComparator


class BaselineComparatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.comparator = BaselineComparator()
        self.temp_dir = Path("tests") / f"_tmp_baseline_compare_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))

        self.verification_report = {
            "status": "passed",
            "passed": True,
            "issues": [],
            "warnings": [],
            "metadata": {"issue_count": 0},
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
            },
            "auto_execution": "none",
        }
        self.metrics_summary = {
            "event_count": 2,
            "metric_count": 4,
            "metrics": {
                "retry_count": {"last": 0, "count": 1},
                "rollback_count": {"last": 0, "count": 1},
                "human_handoff_count": {"last": 0, "count": 1},
                "tool_misuse_count": {"last": 0, "count": 1},
            },
        }
        self.event_trace = {
            "dispatch_trace": [
                {
                    "event_name": "on_verification_report",
                    "event_id": "evt-1",
                    "status": "success",
                    "handler_count": 0,
                    "timestamp": "TIMESTAMP_1",
                },
                {
                    "event_name": "on_journal_append",
                    "event_id": "evt-2",
                    "status": "success",
                    "handler_count": 1,
                    "timestamp": "TIMESTAMP_2",
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
                    "timestamp": "TIMESTAMP_2",
                }
            ],
            "journal_entry": {
                "entry_id": "lesson-1",
                "task_id": "task-1",
                "task_type": "retrieval",
                "tags": ["retrieval", "success"],
                "lesson": "Keep retrieval scope narrow.",
                "source": "success",
                "confidence": 0.65,
                "created_at": "2026-03-28T12:00:00+00:00",
            },
            "learning_journal": {
                "status": "written",
                "written_entry_id": "lesson-1",
                "written_source": "success",
            },
        }

    def test_verification_report_is_compatible_when_structures_match(self) -> None:
        diff_result = self.comparator.compare(
            current=self.verification_report,
            baseline=self.verification_report,
            artifact_type="verification_report",
        )

        self.assertEqual(diff_result["status"], "compatible")
        self.assertEqual(diff_result["missing_fields"], [])
        self.assertEqual(diff_result["type_mismatches"], [])
        self.assertIn("compatible", diff_result["summary"])

    def test_missing_critical_field_is_breaking(self) -> None:
        current = dict(self.verification_report)
        current.pop("issues")

        diff_result = self.comparator.compare(
            current=current,
            baseline=self.verification_report,
            artifact_type="verification_report",
        )

        self.assertEqual(diff_result["status"], "breaking")
        self.assertIn("issues", diff_result["missing_fields"])
        self.assertIn("missing_required_fields", diff_result["reason_codes"])

    def test_unexpected_non_critical_field_is_warning(self) -> None:
        current = dict(self.verification_report)
        current["notes"] = "extra but non-critical"

        diff_result = self.comparator.compare(
            current=current,
            baseline=self.verification_report,
            artifact_type="verification_report",
        )

        self.assertEqual(diff_result["status"], "warning")
        self.assertIn("notes", diff_result["unexpected_fields"])
        self.assertIn("unexpected_fields_present", diff_result["reason_codes"])

    def test_type_mismatch_is_breaking(self) -> None:
        current = dict(self.verification_report)
        current["passed"] = "yes"

        diff_result = self.comparator.compare(
            current=current,
            baseline=self.verification_report,
            artifact_type="verification_report",
        )

        self.assertEqual(diff_result["status"], "breaking")
        self.assertEqual(diff_result["type_mismatches"][0]["field"], "passed")

    def test_event_trace_missing_key_event_is_breaking(self) -> None:
        current = {
            "dispatch_trace": [self.event_trace["dispatch_trace"][0]],
            "execution_status": "success",
        }

        diff_result = self.comparator.compare(
            current=current,
            baseline=self.event_trace,
            artifact_type="event_trace",
        )

        self.assertEqual(diff_result["status"], "breaking")
        self.assertIn("missing_expected_events", diff_result["reason_codes"])
        self.assertIn("on_journal_append", diff_result["value_drifts"][0]["detail"])

    def test_journal_append_trace_with_mirrored_large_object_is_breaking(self) -> None:
        current = json.loads(json.dumps(self.journal_append_trace))
        current["journal_entry"]["sandbox_result"] = {
            "status": "error",
            "snapshot_ref": "snapshot-1",
        }

        diff_result = self.comparator.compare(
            current=current,
            baseline=self.journal_append_trace,
            artifact_type="journal_append_trace",
        )

        self.assertEqual(diff_result["status"], "breaking")
        self.assertIn("journal_payload_bloat_detected", diff_result["reason_codes"])
        self.assertIn("sandbox_result", diff_result["value_drifts"][0]["detail"])

    def test_human_readable_summary_is_clear(self) -> None:
        current = json.loads(json.dumps(self.metrics_summary))
        current["metrics"]["retry_count"]["last"] = 2

        diff_result = self.comparator.compare(
            current=current,
            baseline=self.metrics_summary,
            artifact_type="metrics_summary",
        )

        self.assertEqual(diff_result["status"], "warning")
        self.assertIn("metrics_summary", diff_result["summary"])
        self.assertIn("retry_count", diff_result["summary"])

    def test_load_baseline_handles_unreadable_path_without_crashing(self) -> None:
        missing_path = self.temp_dir / "missing.json"

        load_result = self.comparator.load_baseline(missing_path)

        self.assertEqual(load_result["status"], "error")
        self.assertIn("path_not_readable", load_result["reason_codes"])
        self.assertIn("failed", load_result["summary"].lower())

    def test_load_baseline_reads_explicit_json_file(self) -> None:
        baseline_path = self.temp_dir / "verification.json"
        baseline_path.write_text(json.dumps(self.verification_report), encoding="utf-8")

        load_result = self.comparator.load_baseline(baseline_path)

        self.assertEqual(load_result["status"], "ok")
        self.assertEqual(load_result["data"]["status"], "passed")

    def test_residual_followup_non_advisory_regression_is_breaking(self) -> None:
        current = json.loads(json.dumps(self.residual_followup))
        current["auto_execution"] = "apply_model_escalation"

        diff_result = self.comparator.compare(
            current=current,
            baseline=self.residual_followup,
            artifact_type="residual_followup",
        )

        self.assertEqual(diff_result["status"], "breaking")
        self.assertIn("advisory_boundary_broken", diff_result["reason_codes"])

    def test_structural_compatibility_helper_returns_true_for_metrics_summary(self) -> None:
        compatible = self.comparator.is_structurally_compatible(
            current=self.metrics_summary,
            baseline=self.metrics_summary,
            artifact_type="metrics_summary",
        )

        self.assertTrue(compatible)


if __name__ == "__main__":
    unittest.main()
