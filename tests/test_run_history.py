from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.batch_export import BatchExportOptions, export_batch_results
from entrypoints.batch_runner import SurfaceBatchRequest, load_batch_request_file, run_batch_request
from entrypoints.cli import load_settings, main, run_batch_command
from entrypoints.run_history import (
    append_run_history_entry,
    build_run_history_entry,
    build_run_id,
    list_run_history,
)
from entrypoints.task_runner import SurfaceTaskRequest


class RunHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_run_history_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_manifest_entry_is_minimal_and_stable(self) -> None:
        batch_result, export_result = self._sample_batch_and_export(batch_name="history-entry")
        entry = build_run_history_entry(
            batch_result,
            export_result,
            run_id="fixed-run-id",
            created_at=datetime(2026, 3, 30, 9, 30, 0, tzinfo=timezone.utc),
        )

        payload = entry.as_dict()
        self.assertEqual(
            sorted(payload.keys()),
            [
                "batch_name",
                "completed_tasks",
                "created_at",
                "exported_formats",
                "failed_tasks",
                "notes",
                "output_dir",
                "run_id",
                "stopped_early",
                "tag",
                "total_tasks",
                "written_files",
            ],
        )
        self.assertNotIn("results", payload)
        self.assertNotIn("summary", payload)
        self.assertEqual(payload["run_id"], "fixed-run-id")
        self.assertEqual(payload["batch_name"], "history-entry")

    def test_append_only_jsonl_history_writes_multiple_entries(self) -> None:
        batch_result, export_result = self._sample_batch_and_export(batch_name="append-history")
        history_file = self.temp_dir / "history" / "run_history.jsonl"

        append_run_history_entry(batch_result, export_result, history_file, run_id="run-one")
        append_run_history_entry(batch_result, export_result, history_file, run_id="run-two")

        rows = [json.loads(line) for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["run_id"], "run-one")
        self.assertEqual(rows[1]["run_id"], "run-two")

    def test_run_id_rule_is_stable_and_local(self) -> None:
        created_at = datetime(2026, 3, 30, 10, 11, 12, tzinfo=timezone.utc)
        run_id = build_run_id("Batch Export Demo", created_at=created_at, unique_suffix="abc123")

        self.assertEqual(run_id, "20260330T101112Z_batch_export_demo_abc123")
        self.assertNotEqual(run_id, "")
        self.assertIn("batch_export_demo", run_id)

    def test_listing_helper_reads_entries_and_applies_limit(self) -> None:
        batch_result, export_result = self._sample_batch_and_export(batch_name="list-history")
        history_file = self.temp_dir / "list-history.jsonl"

        append_run_history_entry(batch_result, export_result, history_file, run_id="run-one")
        append_run_history_entry(batch_result, export_result, history_file, run_id="run-two")
        append_run_history_entry(batch_result, export_result, history_file, run_id="run-three")

        all_entries = list_run_history(history_file)
        limited_entries = list_run_history(history_file, limit=2)

        self.assertEqual([item["run_id"] for item in all_entries], ["run-one", "run-two", "run-three"])
        self.assertEqual([item["run_id"] for item in limited_entries], ["run-two", "run-three"])

    def test_cli_batch_export_records_history_with_default_location(self) -> None:
        batch_path = self.temp_dir / "batch.json"
        batch_payload = {
            "batch_name": "cli-history",
            "tasks": [
                {
                    "task": "Review runtime regression output",
                    "task_type": "review",
                    "workflow_profile": "unknown-profile",
                },
                {
                    "task": "Design runtime harness plan",
                    "workflow_profile": "planning design",
                },
            ],
        }
        batch_path.write_text(json.dumps(batch_payload), encoding="utf-8")
        export_dir = self.temp_dir / "cli-history-exports"

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main([
                "run",
                "--batch-file",
                str(batch_path),
                "--output-dir",
                str(export_dir),
            ])

        payload = json.loads(stdout.getvalue())
        self.assertIn(exit_code, {0, 1})
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("run_history", payload)
        history_file = Path(payload["run_history"]["history_file"])
        self.assertEqual(history_file.resolve(), (export_dir / "run_history.jsonl").resolve())
        entries = list_run_history(history_file)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["batch_name"], "cli-history")
        self.assertEqual(entries[0]["exported_formats"], ["json", "jsonl", "markdown"])

    def test_manifest_does_not_mutate_batch_or_export_results(self) -> None:
        batch_result, export_result = self._sample_batch_and_export(batch_name="no-mutation")
        batch_before = deepcopy(batch_result)
        export_before = deepcopy(export_result)

        append_run_history_entry(batch_result, export_result, self.temp_dir / "run_history.jsonl", run_id="run-one")

        self.assertEqual(batch_result, batch_before)
        self.assertEqual(export_result, export_before)
        self.assertNotIn("run_history", batch_result)
        self.assertNotIn("run_id", export_result)

    def test_manifest_write_failure_is_explicit_and_does_not_rewrite_results(self) -> None:
        batch_path = self.temp_dir / "batch.json"
        batch_path.write_text(
            json.dumps(
                {
                    "batch_name": "failing-history",
                    "tasks": [{"task": "Search docs for runtime context"}],
                }
            ),
            encoding="utf-8",
        )
        export_dir = self.temp_dir / "failing-history-exports"

        stdout = StringIO()
        stderr = StringIO()
        with patch("entrypoints.cli.append_run_history_entry", side_effect=RuntimeError("history write failed")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([
                    "run",
                    "--batch-file",
                    str(batch_path),
                    "--output-dir",
                    str(export_dir),
                ])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("history write failed", stderr.getvalue())

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

