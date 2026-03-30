from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.batch_export import BatchExportOptions, export_batch_results
from entrypoints.batch_runner import SurfaceBatchRequest, run_batch_request
from entrypoints.cli import load_settings, main
from entrypoints.history_summary import (
    build_run_history_summary_entry,
    write_latest_run_pointer,
    write_run_history_summary,
)
from entrypoints.run_history import append_run_history_entry, build_run_history_entry, list_run_history
from entrypoints.task_runner import SurfaceTaskRequest


class HistorySummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_history_summary_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_summary_entry_derives_stably_from_run_history_entry(self) -> None:
        batch_result, export_result = self._sample_batch_and_export(batch_name="summary-entry")
        entry = build_run_history_entry(batch_result, export_result, run_id="run-one")
        summary_entry = build_run_history_summary_entry(entry.as_dict()).as_dict()

        self.assertEqual(
            sorted(summary_entry.keys()),
            [
                "batch_name",
                "completed_tasks",
                "created_at",
                "failed_tasks",
                "formats",
                "output_dir",
                "run_id",
                "stopped_early",
                "total_tasks",
            ],
        )
        self.assertNotIn("written_files", summary_entry)
        self.assertEqual(summary_entry["formats"], ["json", "jsonl", "markdown"])

    def test_latest_run_pointer_writes_latest_summary_only(self) -> None:
        history_file = self._append_runs(["run-one", "run-two"], batch_name="latest-pointer")

        pointer_result = write_latest_run_pointer(history_file)

        pointer_path = Path(pointer_result["latest_run_file"])
        payload = json.loads(pointer_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["latest_run"]["run_id"], "run-two")
        self.assertEqual(payload["history_file"], str(history_file))
        self.assertNotIn("written_files", payload["latest_run"])

    def test_history_summary_writes_recent_entries_with_limit(self) -> None:
        history_file = self._append_runs(["run-one", "run-two", "run-three"], batch_name="history-summary")

        summary_result = write_run_history_summary(history_file, limit=2)

        summary_path = Path(summary_result["summary_file"])
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["entry_count"], 2)
        self.assertEqual(payload["limit"], 2)
        self.assertEqual([item["run_id"] for item in payload["entries"]], ["run-two", "run-three"])

    def test_summary_and_pointer_do_not_rewrite_manifest_truth(self) -> None:
        history_file = self._append_runs(["run-one", "run-two"], batch_name="manifest-truth")
        before_entries = deepcopy(list_run_history(history_file))

        write_latest_run_pointer(history_file)
        write_run_history_summary(history_file, limit=1)

        after_entries = list_run_history(history_file)
        self.assertEqual(before_entries, after_entries)

    def test_cli_writes_latest_run_and_optional_history_summary(self) -> None:
        batch_path = self.temp_dir / "batch.json"
        batch_path.write_text(
            json.dumps(
                {
                    "batch_name": "cli-summary",
                    "tasks": [
                        {"task": "Review runtime regression output", "task_type": "review"},
                        {"task": "Design runtime harness plan", "workflow_profile": "planning design"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        export_dir = self.temp_dir / "cli-summary-exports"

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                [
                    "run",
                    "--batch-file",
                    str(batch_path),
                    "--output-dir",
                    str(export_dir),
                    "--write-history-summary",
                    "--history-summary-limit",
                    "1",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertIn(exit_code, {0, 1})
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("history_index", payload)
        latest_run_file = Path(payload["history_index"]["latest_run"]["latest_run_file"])
        history_summary_file = Path(payload["history_index"]["history_summary"]["summary_file"])
        self.assertTrue(latest_run_file.exists())
        self.assertTrue(history_summary_file.exists())

    def test_summary_and_pointer_failure_is_explicit(self) -> None:
        batch_path = self.temp_dir / "batch.json"
        batch_path.write_text(
            json.dumps({"batch_name": "failing-summary", "tasks": [{"task": "Search docs for runtime context"}]}),
            encoding="utf-8",
        )
        export_dir = self.temp_dir / "failing-summary-exports"

        stdout = StringIO()
        stderr = StringIO()
        with patch("entrypoints.cli.write_latest_run_pointer", side_effect=RuntimeError("latest run write failed")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["run", "--batch-file", str(batch_path), "--output-dir", str(export_dir)])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("latest run write failed", stderr.getvalue())

    def test_summary_files_do_not_include_internal_evaluation_payloads(self) -> None:
        history_file = self._append_runs(["run-one"], batch_name="schema-clean")

        pointer_path = Path(write_latest_run_pointer(history_file)["latest_run_file"])
        summary_path = Path(write_run_history_summary(history_file, limit=1)["summary_file"])
        pointer_payload = json.loads(pointer_path.read_text(encoding="utf-8"))
        summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertNotIn("evaluation_input_bundle", json.dumps(pointer_payload, ensure_ascii=True))
        self.assertNotIn("realm_evaluation", json.dumps(summary_payload, ensure_ascii=True))

    def _append_runs(self, run_ids: list[str], *, batch_name: str) -> Path:
        batch_result, export_result = self._sample_batch_and_export(batch_name=batch_name)
        history_file = self.temp_dir / batch_name / "run_history.jsonl"
        for run_id in run_ids:
            append_run_history_entry(batch_result, export_result, history_file, run_id=run_id)
        return history_file

    def _sample_batch_and_export(self, *, batch_name: str) -> tuple[dict[str, object], dict[str, object]]:
        batch_result = run_batch_request(
            SurfaceBatchRequest(
                tasks=[
                    SurfaceTaskRequest(task="Search docs for runtime context"),
                    SurfaceTaskRequest(task="Review runtime regression output", task_type="review"),
                ],
                batch_name=batch_name,
            ),
            load_settings(),
        )
        export_result = export_batch_results(
            batch_result,
            BatchExportOptions(output_dir=self.temp_dir / f"{batch_name}-exports"),
        )
        return batch_result, export_result


if __name__ == "__main__":
    unittest.main()
