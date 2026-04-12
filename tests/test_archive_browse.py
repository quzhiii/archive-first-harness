from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.archive_browse import (
    browse_run_archives,
    compare_run_archives,
    find_run_archive,
    format_archive_brief,
    read_latest_run_archive,
    summarize_run_archives,
)
from entrypoints.cli import load_settings, main
from entrypoints.run_archive import write_run_archive
from entrypoints.task_runner import SurfaceTaskRequest, run_task_request


class FailingExecutor:
    def execute_step(self, step, available_tools, working_context):
        return {
            "status": "error",
            "tool_name": step.get("tool_name"),
            "output": None,
            "error": {
                "type": "surface_execution_failure",
                "message": "forced failure for archive browse test",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


class ArchiveBrowseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_archive_browse_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.archive_root = self.temp_dir / "manual-runs"
        self.base_time = datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)

    def test_browse_run_archives_filters_recent_rows(self) -> None:
        self._write_success_archive(
            run_id="run-success-a",
            task_type="research",
            minutes_offset=0,
            formation_id="discovery",
        )
        self._write_failed_archive(
            run_id="run-failed-review",
            task_type="review",
            minutes_offset=1,
            formation_id="review",
        )
        self._write_success_archive(
            run_id="run-success-b",
            task_type="research",
            minutes_offset=2,
            formation_id="delivery",
        )

        payload = browse_run_archives(
            self.archive_root,
            limit=2,
            workflow_profile_id="evaluation_regression",
            task_type="review",
            formation_id="review",
            status="failed",
            failure_class="surface_execution_failure",
        )
        output = format_archive_brief(payload)

        self.assertEqual(payload["source"], "index_file")
        self.assertEqual(payload["entry_count"], 1)
        self.assertEqual(payload["filters"]["task_type"], "review")
        self.assertEqual(payload["filters"]["formation_id"], "review")
        self.assertEqual(payload["entries"][0]["run_id"], "run-failed-review")
        self.assertEqual(payload["entries"][0]["task_type"], "review")
        self.assertEqual(payload["entries"][0]["formation_id"], "review")
        self.assertIn(
            "filters: workflow_profile_id=evaluation_regression task_type=review formation_id=review status=failed failure_class=surface_execution_failure",
            output,
        )
        self.assertIn(
            "task_type=review | formation=review | status=failed | failure=surface_execution_failure | governance=clear | gov_required=no | missing_expected=no",
            output,
        )

    def test_browse_summary_surfaces_governance_and_missing_expected_warning(
        self,
    ) -> None:
        self._write_governance_review_archive(
            run_id="run-governance-review", task_type="research", minutes_offset=0
        )
        self._write_missing_expected_artifact_archive(
            run_id="run-missing-artifact", task_type="coding", minutes_offset=1
        )

        governance_output = format_archive_brief(
            browse_run_archives(self.archive_root, limit=5, task_type="research")
        )
        warning_output = format_archive_brief(
            browse_run_archives(self.archive_root, limit=5, task_type="coding")
        )

        self.assertIn(
            "governance=review_required | gov_required=yes | missing_expected=no",
            governance_output,
        )
        self.assertIn(
            "governance=clear | gov_required=no | missing_expected=yes", warning_output
        )

    def test_summarize_run_archives_aggregates_filtered_trends(self) -> None:
        self._write_success_archive(
            run_id="run-success-a",
            task_type="research",
            minutes_offset=0,
            formation_id="discovery",
        )
        self._write_governance_review_archive(
            run_id="run-governance-review",
            task_type="research",
            minutes_offset=1,
            formation_id="review",
        )
        self._write_failed_archive(
            run_id="run-failed-review",
            task_type="review",
            minutes_offset=2,
            formation_id="review",
        )

        payload = summarize_run_archives(self.archive_root, task_type="research")
        output = format_archive_brief(payload)

        self.assertEqual(payload["entry_count"], 2)
        self.assertEqual(payload["status_counts"], {"success": 2})
        self.assertEqual(payload["task_type_counts"], {"research": 2})
        self.assertEqual(payload["formation_counts"], {"discovery": 1, "review": 1})
        self.assertEqual(
            payload["governance_status_counts"], {"clear": 1, "review_required": 1}
        )
        self.assertEqual(
            payload["missing_expected_warning_counts"], {"yes": 0, "no": 2}
        )
        self.assertEqual(payload["oldest"]["run_id"], "run-success-a")
        self.assertEqual(payload["latest"]["run_id"], "run-governance-review")
        self.assertIn("Archive trend summary", output)
        self.assertIn("entry_count: 2", output)
        self.assertIn(
            "filters: workflow_profile_id=any task_type=research formation_id=any status=any failure_class=any",
            output,
        )
        self.assertIn("status_counts: success:2", output)
        self.assertIn("formation_counts: discovery:1,review:1", output)
        self.assertIn("governance_status_counts: clear:1,review_required:1", output)

    def test_summarize_run_archives_empty_result_is_human_readable(self) -> None:
        self._write_success_archive(
            run_id="run-success-a", task_type="research", minutes_offset=0
        )

        payload = summarize_run_archives(self.archive_root, task_type="coding")
        output = format_archive_brief(payload)

        self.assertEqual(payload["entry_count"], 0)
        self.assertEqual(payload["status_counts"], {})
        self.assertEqual(payload["task_type_counts"], {})
        self.assertIn("Archive trend summary", output)
        self.assertIn("entry_count: 0", output)
        self.assertIn("range: none", output)
        self.assertIn("status_counts: none", output)
        self.assertIn("missing_expected_warning_counts: yes:0,no:0", output)

    def test_read_latest_run_archive_prefers_index_and_falls_back_to_directory_scan(
        self,
    ) -> None:
        self._write_success_archive(
            run_id="run-success-a",
            task_type="research",
            minutes_offset=0,
            formation_id="discovery",
        )
        self._write_failed_archive(
            run_id="run-failed-review",
            task_type="review",
            minutes_offset=1,
            formation_id="review",
        )

        latest_payload = read_latest_run_archive(self.archive_root)
        self.assertEqual(latest_payload["source"], "index_file")
        self.assertEqual(
            latest_payload["latest_archive"]["run_id"], "run-failed-review"
        )

        (self.archive_root / "index.jsonl").unlink()

        fallback_latest = read_latest_run_archive(self.archive_root)
        fallback_browse = browse_run_archives(
            self.archive_root, limit=5, status="failed"
        )

        self.assertEqual(fallback_latest["source"], "archive_dirs")
        self.assertEqual(
            fallback_latest["latest_archive"]["run_id"], "run-failed-review"
        )
        self.assertEqual(fallback_browse["source"], "archive_dirs")
        self.assertEqual(
            [item["run_id"] for item in fallback_browse["entries"]],
            ["run-failed-review"],
        )

    def test_find_run_archive_returns_minimal_diagnostic_bundle(self) -> None:
        self._write_success_archive(
            run_id="run-success-a", task_type="research", minutes_offset=0
        )

        payload = find_run_archive(self.archive_root, "run-success-a")
        output = format_archive_brief(payload)

        self.assertEqual(payload["entry"]["run_id"], "run-success-a")
        self.assertEqual(payload["archive"]["manifest"]["status"], "success")
        self.assertEqual(payload["archive"]["verification_report"]["status"], "passed")
        self.assertIn("Archive entry", output)
        self.assertIn("run_id: run-success-a", output)
        self.assertIn("verification_status: passed", output)
        self.assertIn("expected_artifacts: report", output)
        self.assertIn("produced_artifacts: none", output)
        self.assertIn("produced_artifact_count: 0", output)
        self.assertIn("baseline_compare_status: not_requested", output)
        self.assertNotIn("execution_result", output)
        self.assertNotIn("{", output)

    def test_compare_run_archives_surfaces_reassessment_and_evaluation_changes(
        self,
    ) -> None:
        self._write_success_archive(
            run_id="run-success-a",
            task_type="research",
            minutes_offset=0,
            formation_id="discovery",
        )
        self._write_failed_archive(
            run_id="run-failed-review",
            task_type="review",
            minutes_offset=1,
            formation_id="review",
        )

        payload = compare_run_archives(
            self.archive_root, "run-success-a", "run-failed-review"
        )
        output = format_archive_brief(payload)

        self.assertNotEqual(
            payload["left"]["reassessed_level"], payload["right"]["reassessed_level"]
        )
        self.assertEqual(payload["right"]["reassessed_level"], "high")
        self.assertEqual(payload["left"]["task_type"], "research")
        self.assertEqual(payload["right"]["task_type"], "review")
        self.assertEqual(payload["left"]["formation_id"], "discovery")
        self.assertEqual(payload["right"]["formation_id"], "review")
        self.assertFalse(payload["left"]["followup_needed"])
        self.assertTrue(payload["right"]["followup_needed"])
        self.assertEqual(payload["left"]["evaluation_recommendation"], "keep")
        self.assertEqual(payload["right"]["evaluation_recommendation"], "observe")
        self.assertFalse(payload["left"]["evaluation_human_review"])
        self.assertTrue(payload["right"]["evaluation_human_review"])
        self.assertEqual(
            payload["left"]["reassessment_reason_codes"], ["execution_clean"]
        )
        self.assertEqual(
            payload["right"]["reassessment_reason_codes"],
            ["execution_failed", "verification_issues_present"],
        )
        self.assertEqual(
            payload["left"]["evaluation_reason_codes"], ["stable_baseline"]
        )
        self.assertEqual(
            payload["right"]["evaluation_reason_codes"], ["execution_failure_detected"]
        )
        self.assertFalse(payload["comparison"]["same_task_type"])
        self.assertFalse(payload["comparison"]["same_formation_id"])
        self.assertFalse(payload["comparison"]["same_reassessed_level"])
        self.assertFalse(payload["comparison"]["same_followup_needed"])
        self.assertFalse(payload["comparison"]["same_reassessment_reason_codes"])
        self.assertEqual(
            payload["comparison"]["reassessment_reason_codes_added"],
            ["execution_failed", "verification_issues_present"],
        )
        self.assertEqual(
            payload["comparison"]["reassessment_reason_codes_removed"],
            ["execution_clean"],
        )
        self.assertFalse(payload["comparison"]["same_evaluation_recommendation"])
        self.assertFalse(payload["comparison"]["same_evaluation_human_review"])
        self.assertFalse(payload["comparison"]["same_evaluation_reason_codes"])
        self.assertEqual(
            payload["comparison"]["evaluation_reason_codes_added"],
            ["execution_failure_detected"],
        )
        self.assertEqual(
            payload["comparison"]["evaluation_reason_codes_removed"],
            ["stable_baseline"],
        )
        self.assertEqual(payload["comparison"]["reassessment_transition"], "regressed")
        self.assertEqual(payload["comparison"]["evaluation_transition"], "regressed")
        self.assertIn("Archive comparison", output)
        self.assertIn("task_type=research | formation=discovery", output)
        self.assertIn("task_type=review | formation=review", output)
        self.assertIn("same_task_type=no same_formation=no", output)
        self.assertIn(
            "transitions: failure=regressed verification=regressed reassessment=regressed evaluation=regressed governance=unchanged artifacts=changed",
            output,
        )
        self.assertIn(
            "artifact_diff: transition=changed expected(+audit_note; -report) status_counts(left=none right=none) missing_expected=no->no",
            output,
        )
        self.assertNotIn("produced(+none; -none)", output)
        self.assertNotIn("baseline(+none; -none)", output)
        self.assertIn(
            "reason_code_diff: reassessment(+execution_failed,verification_issues_present; -execution_clean) evaluation(+execution_failure_detected; -stable_baseline)",
            output,
        )
        self.assertIn(
            "highlights: failure regressed; verification regressed; risk regressed; evaluation regressed; artifacts changed; reassessment reasons +execution_failed,verification_issues_present -execution_clean; evaluation reasons +execution_failure_detected -stable_baseline; expected artifacts +audit_note -report",
            output,
        )

    def test_compare_run_archives_surfaces_governance_changes(self) -> None:
        self._write_success_archive(
            run_id="run-success-a", task_type="research", minutes_offset=0
        )
        self._write_governance_review_archive(
            run_id="run-governance-review", task_type="research", minutes_offset=1
        )

        payload = compare_run_archives(
            self.archive_root, "run-success-a", "run-governance-review"
        )
        output = format_archive_brief(payload)

        self.assertEqual(payload["left"]["verification_status"], "passed")
        self.assertEqual(payload["right"]["verification_status"], "passed")
        self.assertEqual(payload["left"]["governance_status"], "clear")
        self.assertEqual(payload["right"]["governance_status"], "review_required")
        self.assertTrue(payload["comparison"]["same_reassessment_reason_codes"])
        self.assertEqual(payload["comparison"]["reassessment_reason_codes_added"], [])
        self.assertEqual(payload["comparison"]["reassessment_reason_codes_removed"], [])
        self.assertTrue(payload["comparison"]["same_evaluation_reason_codes"])
        self.assertEqual(payload["comparison"]["evaluation_reason_codes_added"], [])
        self.assertEqual(payload["comparison"]["evaluation_reason_codes_removed"], [])
        self.assertFalse(payload["comparison"]["same_governance_status"])
        self.assertFalse(payload["comparison"]["same_governance_required"])
        self.assertEqual(payload["comparison"]["failure_transition"], "regressed")
        self.assertEqual(payload["comparison"]["verification_transition"], "unchanged")
        self.assertEqual(payload["comparison"]["reassessment_transition"], "unchanged")
        self.assertEqual(payload["comparison"]["evaluation_transition"], "unchanged")
        self.assertEqual(payload["comparison"]["governance_transition"], "escalated")
        self.assertIn("Archive comparison", output)
        self.assertIn(
            "reason_code_diff: reassessment(+none; -none) evaluation(+none; -none)",
            output,
        )
        self.assertIn("highlights: failure regressed; governance escalated", output)
        self.assertIn(
            "transitions: failure=regressed verification=unchanged reassessment=unchanged evaluation=unchanged governance=escalated",
            output,
        )

    def test_compare_run_archives_surfaces_artifact_summary_changes(self) -> None:
        self._write_success_archive(
            run_id="run-success-a",
            task_type="research",
            minutes_offset=0,
            formation_id="discovery",
        )
        self._write_artifact_signal_archive(
            run_id="run-artifact-signal",
            task_type="research",
            minutes_offset=1,
            formation_id="discovery",
        )

        payload = compare_run_archives(
            self.archive_root, "run-success-a", "run-artifact-signal"
        )
        output = format_archive_brief(payload)

        self.assertEqual(payload["left"]["expected_artifacts"], ["report"])
        self.assertEqual(payload["right"]["expected_artifacts"], ["code_patch"])
        self.assertEqual(payload["left"]["produced_artifact_types"], [])
        self.assertEqual(payload["right"]["produced_artifact_types"], ["file_change"])
        self.assertEqual(payload["left"]["produced_artifact_count"], 0)
        self.assertEqual(payload["right"]["produced_artifact_count"], 1)
        self.assertEqual(payload["left"]["baseline_compare_status"], "not_requested")
        self.assertEqual(payload["right"]["baseline_compare_status"], "completed")
        self.assertEqual(payload["left"]["baseline_compared_artifact_types"], [])
        self.assertEqual(
            payload["right"]["baseline_compared_artifact_types"],
            ["metrics_summary", "verification_report"],
        )
        self.assertEqual(payload["left"]["baseline_status_counts"], {})
        self.assertEqual(
            payload["right"]["baseline_status_counts"], {"compatible": 1, "warning": 1}
        )
        self.assertFalse(payload["comparison"]["same_expected_artifacts"])
        self.assertFalse(payload["comparison"]["same_produced_artifact_types"])
        self.assertFalse(payload["comparison"]["same_produced_artifact_count"])
        self.assertFalse(payload["comparison"]["same_baseline_compare_status"])
        self.assertFalse(payload["comparison"]["same_baseline_compared_artifact_types"])
        self.assertFalse(payload["comparison"]["same_baseline_status_counts"])
        self.assertEqual(
            payload["comparison"]["expected_artifacts_added"], ["code_patch"]
        )
        self.assertEqual(
            payload["comparison"]["expected_artifacts_removed"], ["report"]
        )
        self.assertEqual(
            payload["comparison"]["produced_artifact_types_added"], ["file_change"]
        )
        self.assertEqual(payload["comparison"]["produced_artifact_types_removed"], [])
        self.assertEqual(
            payload["comparison"]["baseline_compared_artifact_types_added"],
            ["metrics_summary", "verification_report"],
        )
        self.assertEqual(
            payload["comparison"]["baseline_compared_artifact_types_removed"], []
        )
        self.assertEqual(payload["comparison"]["artifact_transition"], "regressed")
        self.assertIn(
            "transitions: failure=unchanged verification=unchanged reassessment=unchanged evaluation=unchanged governance=unchanged artifacts=regressed",
            output,
        )
        self.assertIn(
            "artifacts_left: expected=report produced=none(0) baseline_status=not_requested baseline_artifacts=none status_counts=none missing_expected=no",
            output,
        )
        self.assertIn(
            "artifacts_right: expected=code_patch produced=file_change(1) baseline_status=completed baseline_artifacts=metrics_summary,verification_report status_counts=compatible:1,warning:1 missing_expected=no",
            output,
        )
        self.assertIn(
            "artifact_diff: transition=regressed expected(+code_patch; -report) produced(+file_change; -none) baseline(+metrics_summary,verification_report; -none) status_counts(left=none right=compatible:1,warning:1) missing_expected=no->no",
            output,
        )
        self.assertIn(
            "highlights: artifacts regressed; expected artifacts +code_patch -report; produced artifacts +file_change; baseline artifacts +metrics_summary,verification_report",
            output,
        )

    def test_archive_browse_tolerates_malformed_index_lines(self) -> None:
        self._write_success_archive(
            run_id="run-success-a", task_type="research", minutes_offset=0
        )
        self._write_success_archive(
            run_id="run-success-b", task_type="research", minutes_offset=1
        )
        index_file = self.archive_root / "index.jsonl"
        index_file.write_text(
            index_file.read_text(encoding="utf-8") + "}\n", encoding="utf-8"
        )

        latest_payload = read_latest_run_archive(self.archive_root)
        browse_payload = browse_run_archives(self.archive_root, limit=5)

        self.assertEqual(latest_payload["source"], "index_file+archive_dirs")
        self.assertEqual(latest_payload["latest_archive"]["run_id"], "run-success-b")
        self.assertEqual(browse_payload["source"], "index_file+archive_dirs")
        self.assertEqual(
            [item["run_id"] for item in browse_payload["entries"]],
            ["run-success-a", "run-success-b"],
        )

    def test_archive_browse_recovers_missing_index_rows_from_archive_dirs(self) -> None:
        self._write_success_archive(
            run_id="run-success-a", task_type="research", minutes_offset=0
        )
        self._write_success_archive(
            run_id="run-success-b", task_type="research", minutes_offset=1
        )
        index_file = self.archive_root / "index.jsonl"
        lines = index_file.read_text(encoding="utf-8").splitlines()
        index_file.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

        latest_payload = read_latest_run_archive(self.archive_root)
        lookup_payload = find_run_archive(self.archive_root, "run-success-b")

        self.assertEqual(latest_payload["source"], "index_file+archive_dirs")
        self.assertEqual(latest_payload["latest_archive"]["run_id"], "run-success-b")
        self.assertEqual(lookup_payload["source"], "index_file+archive_dirs")
        self.assertEqual(lookup_payload["entry"]["run_id"], "run-success-b")

    def test_cli_archive_latest_lookup_and_compare_are_human_readable(self) -> None:
        self._write_success_archive(
            run_id="run-success-a",
            task_type="research",
            minutes_offset=0,
            formation_id="discovery",
        )
        self._write_governance_review_archive(
            run_id="run-governance-review",
            task_type="research",
            minutes_offset=1,
            formation_id="review",
        )

        browse_stdout = StringIO()
        browse_stderr = StringIO()
        with redirect_stdout(browse_stdout), redirect_stderr(browse_stderr):
            browse_exit_code = main(
                [
                    "archive",
                    "--archive-root",
                    str(self.archive_root),
                    "--task-type",
                    "research",
                    "--formation-id",
                    "discovery",
                ]
            )

        latest_stdout = StringIO()
        latest_stderr = StringIO()
        with redirect_stdout(latest_stdout), redirect_stderr(latest_stderr):
            latest_exit_code = main(
                [
                    "archive",
                    "--archive-root",
                    str(self.archive_root),
                    "--latest",
                ]
            )

        lookup_stdout = StringIO()
        lookup_stderr = StringIO()
        with redirect_stdout(lookup_stdout), redirect_stderr(lookup_stderr):
            lookup_exit_code = main(
                [
                    "archive",
                    "--archive-root",
                    str(self.archive_root),
                    "--run-id",
                    "run-success-a",
                ]
            )

        compare_stdout = StringIO()
        compare_stderr = StringIO()
        with redirect_stdout(compare_stdout), redirect_stderr(compare_stderr):
            compare_exit_code = main(
                [
                    "archive",
                    "--archive-root",
                    str(self.archive_root),
                    "--compare-run-id",
                    "run-success-a",
                    "--compare-run-id",
                    "run-governance-review",
                ]
            )

        self.assertEqual(browse_exit_code, 0)
        self.assertEqual(browse_stderr.getvalue(), "")
        self.assertIn("Archive summary", browse_stdout.getvalue())
        self.assertIn(
            "task_type=research formation_id=discovery", browse_stdout.getvalue()
        )
        self.assertIn(
            "task_type=research | formation=discovery", browse_stdout.getvalue()
        )
        self.assertNotIn("{", browse_stdout.getvalue())

        self.assertEqual(latest_exit_code, 0)
        self.assertEqual(latest_stderr.getvalue(), "")
        self.assertIn("Latest archive", latest_stdout.getvalue())
        self.assertIn("run_id: run-governance-review", latest_stdout.getvalue())
        self.assertNotIn("{", latest_stdout.getvalue())

        self.assertEqual(lookup_exit_code, 0)
        self.assertEqual(lookup_stderr.getvalue(), "")
        self.assertIn("Archive entry", lookup_stdout.getvalue())
        self.assertIn("run_id: run-success-a", lookup_stdout.getvalue())
        self.assertNotIn("{", lookup_stdout.getvalue())

        self.assertEqual(compare_exit_code, 0)
        self.assertEqual(compare_stderr.getvalue(), "")
        self.assertIn("Archive comparison", compare_stdout.getvalue())
        self.assertIn("governance=escalated", compare_stdout.getvalue())
        self.assertIn(
            "highlights: failure regressed; governance escalated",
            compare_stdout.getvalue(),
        )
        self.assertNotIn("{", compare_stdout.getvalue())

    def test_cli_archive_summary_is_human_readable(self) -> None:
        self._write_success_archive(
            run_id="run-success-a",
            task_type="research",
            minutes_offset=0,
            formation_id="discovery",
        )
        self._write_governance_review_archive(
            run_id="run-governance-review",
            task_type="research",
            minutes_offset=1,
            formation_id="review",
        )
        self._write_failed_archive(
            run_id="run-failed-review",
            task_type="review",
            minutes_offset=2,
            formation_id="review",
        )

        summary_stdout = StringIO()
        summary_stderr = StringIO()
        with redirect_stdout(summary_stdout), redirect_stderr(summary_stderr):
            summary_exit_code = main(
                [
                    "archive",
                    "--archive-root",
                    str(self.archive_root),
                    "--summary",
                    "--task-type",
                    "research",
                ]
            )

        self.assertEqual(summary_exit_code, 0)
        self.assertEqual(summary_stderr.getvalue(), "")
        self.assertIn("Archive trend summary", summary_stdout.getvalue())
        self.assertIn("entry_count: 2", summary_stdout.getvalue())
        self.assertIn("status_counts: success:2", summary_stdout.getvalue())
        self.assertIn(
            "governance_status_counts: clear:1,review_required:1",
            summary_stdout.getvalue(),
        )
        self.assertNotIn("{", summary_stdout.getvalue())

    def test_archive_browse_is_read_only_and_does_not_mutate_index(self) -> None:
        self._write_success_archive(
            run_id="run-success-a", task_type="research", minutes_offset=0
        )
        self._write_failed_archive(
            run_id="run-failed-review", task_type="review", minutes_offset=1
        )
        index_file = self.archive_root / "index.jsonl"
        before_index = index_file.read_text(encoding="utf-8")
        archive_dir = self.archive_root / "run-success-a"
        before_manifest = (archive_dir / "manifest.json").read_text(encoding="utf-8")

        browse_run_archives(self.archive_root, limit=5, status="failed")
        read_latest_run_archive(self.archive_root)
        find_run_archive(self.archive_root, "run-success-a")
        compare_run_archives(self.archive_root, "run-success-a", "run-failed-review")

        self.assertEqual(index_file.read_text(encoding="utf-8"), before_index)
        self.assertEqual(
            (archive_dir / "manifest.json").read_text(encoding="utf-8"), before_manifest
        )

    def test_archive_browse_missing_run_id_is_explicit(self) -> None:
        self._write_success_archive(
            run_id="run-success-a", task_type="research", minutes_offset=0
        )

        with self.assertRaisesRegex(LookupError, "run_id not found: missing-run"):
            find_run_archive(self.archive_root, "missing-run")

    def _created_at(self, minutes_offset: int) -> datetime:
        return self.base_time + timedelta(minutes=minutes_offset)

    def _write_success_archive(
        self,
        *,
        run_id: str,
        task_type: str,
        minutes_offset: int,
        formation_id: str = "default",
    ) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task=f"Task for {run_id}", task_type=task_type),
            load_settings(),
        )
        write_run_archive(
            archive_root=self.archive_root,
            run_id=run_id,
            run_result=result,
            created_at=self._created_at(minutes_offset),
            surface_request={"task": f"Task for {run_id}"},
            formation_id=formation_id,
        )

    def _write_failed_archive(
        self,
        *,
        run_id: str,
        task_type: str,
        minutes_offset: int,
        formation_id: str = "default",
    ) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task=f"Task for {run_id}", task_type=task_type),
            load_settings(),
            executor=FailingExecutor(),
        )
        write_run_archive(
            archive_root=self.archive_root,
            run_id=run_id,
            run_result=result,
            created_at=self._created_at(minutes_offset),
            surface_request={"task": f"Task for {run_id}"},
            formation_id=formation_id,
        )

    def _write_governance_review_archive(
        self,
        *,
        run_id: str,
        task_type: str,
        minutes_offset: int,
        formation_id: str = "default",
    ) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task=f"Task for {run_id}", task_type=task_type),
            load_settings(),
        )
        modified_result = deepcopy(result)
        modified_result["residual_followup"]["governance"] = {
            "status": "review_required",
            "approved": False,
            "requires_governance_override": True,
            "issues": [{"code": "methodology_out_of_contract"}],
        }
        write_run_archive(
            archive_root=self.archive_root,
            run_id=run_id,
            run_result=modified_result,
            created_at=self._created_at(minutes_offset),
            surface_request={"task": f"Task for {run_id}"},
            formation_id=formation_id,
        )

    def _write_artifact_signal_archive(
        self,
        *,
        run_id: str,
        task_type: str,
        minutes_offset: int,
        formation_id: str = "default",
    ) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task=f"Task for {run_id}", task_type=task_type),
            load_settings(),
        )
        modified_result = deepcopy(result)
        modified_result["task_contract"]["expected_artifacts"] = ["code_patch"]
        modified_result["execution_result"]["artifacts"] = [
            {"type": "file_change", "path": "artifacts/generated_patch.diff"}
        ]
        modified_result["baseline_compare_results"] = {
            "status": "completed",
            "compared_artifact_types": ["verification_report", "metrics_summary"],
            "artifact_results": {
                "verification_report": {
                    "artifact_type": "verification_report",
                    "status": "compatible",
                },
                "metrics_summary": {
                    "artifact_type": "metrics_summary",
                    "status": "warning",
                },
            },
            "status_counts": {"compatible": 1, "warning": 1},
        }
        evaluation_input_bundle = modified_result.get("evaluation_input_bundle")
        if isinstance(evaluation_input_bundle, dict):
            task_contract_summary = evaluation_input_bundle.get("task_contract_summary")
            if isinstance(task_contract_summary, dict):
                task_contract_summary["expected_artifacts"] = ["code_patch"]
        write_run_archive(
            archive_root=self.archive_root,
            run_id=run_id,
            run_result=modified_result,
            created_at=self._created_at(minutes_offset),
            surface_request={"task": f"Task for {run_id}"},
            formation_id=formation_id,
        )

    def _write_missing_expected_artifact_archive(
        self,
        *,
        run_id: str,
        task_type: str,
        minutes_offset: int,
        formation_id: str = "default",
    ) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task=f"Task for {run_id}", task_type=task_type),
            load_settings(),
        )
        modified_result = deepcopy(result)
        modified_result["task_contract"]["expected_artifacts"] = ["code_patch"]
        modified_result["execution_result"]["artifacts"] = []
        modified_result["verification_report"]["warnings"] = [
            {
                "code": "missing_expected_artifact",
                "message": "task contract expects a code_patch but execution_result has no artifacts",
            }
        ]
        write_run_archive(
            archive_root=self.archive_root,
            run_id=run_id,
            run_result=modified_result,
            created_at=self._created_at(minutes_offset),
            surface_request={"task": f"Task for {run_id}"},
            formation_id=formation_id,
        )


if __name__ == "__main__":
    unittest.main()
