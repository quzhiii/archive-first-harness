from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
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
from entrypoints.history_browse import browse_run_history, read_latest_run, read_run_history_summary
from entrypoints.history_summary import write_latest_run_pointer, write_run_history_summary
from entrypoints.run_history import append_run_history_entry
from entrypoints.task_runner import SurfaceTaskRequest


class HistoryBrowseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_history_browse_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_read_latest_run_prefers_latest_pointer_when_present(self) -> None:
        history_file = self._append_runs(["run-one", "run-two"], batch_name="latest-present")
        write_latest_run_pointer(history_file)

        payload = read_latest_run(history_file)

        self.assertEqual(payload["source"], "latest_run_file")
        self.assertEqual(payload["latest_run"]["run_id"], "run-two")
        self.assertEqual(payload["latest_run"]["batch_name"], "latest-present")

    def test_read_latest_run_falls_back_to_manifest_without_writing_pointer(self) -> None:
        history_file = self._append_runs(["run-one", "run-two"], batch_name="latest-fallback")
        latest_run_file = history_file.parent / "latest_run.json"

        payload = read_latest_run(history_file)

        self.assertEqual(payload["source"], "manifest")
        self.assertEqual(payload["latest_run"]["run_id"], "run-two")
        self.assertFalse(latest_run_file.exists())

    def test_read_summary_uses_summary_file_and_applies_limit(self) -> None:
        history_file = self._append_runs(["run-one", "run-two", "run-three"], batch_name="summary-present")
        write_run_history_summary(history_file, limit=3)

        payload = read_run_history_summary(history_file, limit=2)

        self.assertEqual(payload["source"], "summary_file")
        self.assertEqual(payload["entry_count"], 2)
        self.assertEqual([item["run_id"] for item in payload["entries"]], ["run-two", "run-three"])

    def test_read_summary_can_still_use_summary_file_when_manifest_is_missing(self) -> None:
        history_file = self._append_runs(["run-one", "run-two"], batch_name="summary-only")
        write_run_history_summary(history_file, limit=2)
        history_file.unlink()

        payload = read_run_history_summary(history_file, limit=10)

        self.assertEqual(payload["source"], "summary_file")
        self.assertEqual([item["run_id"] for item in payload["entries"]], ["run-one", "run-two"])

    def test_read_summary_falls_back_to_manifest_without_writing_summary_file(self) -> None:
        history_file = self._append_runs(["run-one", "run-two", "run-three"], batch_name="summary-fallback")
        summary_file = history_file.parent / "run_history_summary.json"

        payload = read_run_history_summary(history_file, limit=2)

        self.assertEqual(payload["source"], "manifest")
        self.assertEqual([item["run_id"] for item in payload["entries"]], ["run-two", "run-three"])
        self.assertFalse(summary_file.exists())

    def test_browse_run_history_prefers_summary_and_falls_back_to_manifest(self) -> None:
        history_file = self._append_runs(["run-one", "run-two", "run-three"], batch_name="browse-history")

        manifest_payload = browse_run_history(history_file, limit=2)
        write_run_history_summary(history_file, limit=3)
        summary_payload = browse_run_history(history_file, limit=2)

        self.assertEqual(manifest_payload["source"], "manifest")
        self.assertEqual(summary_payload["source"], "summary_file")
        self.assertEqual([item["run_id"] for item in summary_payload["entries"]], ["run-two", "run-three"])

    def test_cli_history_latest_prints_minimal_latest_run_output(self) -> None:
        history_file = self._append_runs(["run-one", "run-two"], batch_name="cli-latest")
        write_latest_run_pointer(history_file)

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["history", "--history-file", str(history_file), "--latest"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Latest run", output)
        self.assertIn("run_id: run-two", output)
        self.assertIn("batch_name: cli-latest", output)
        self.assertNotIn("{", output)

    def test_cli_history_summary_prints_recent_entries(self) -> None:
        history_file = self._append_runs(["run-one", "run-two", "run-three"], batch_name="cli-summary")

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["history", "--history-file", str(history_file), "--summary", "--limit", "2"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("History summary", output)
        self.assertIn("- run-two |", output)
        self.assertIn("- run-three |", output)
        self.assertNotIn("- run-one |", output)

    def test_cli_history_defaults_to_recent_browse_output(self) -> None:
        history_file = self._append_runs(["run-one", "run-two", "run-three"], batch_name="cli-browse")

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["history", "--history-file", str(history_file), "--limit", "1"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("History summary", output)
        self.assertIn("- run-three |", output)
        self.assertNotIn("- run-one |", output)
        self.assertNotIn("- run-two |", output)

    def test_history_browse_is_read_only_and_does_not_mutate_manifest(self) -> None:
        history_file = self._append_runs(["run-one", "run-two"], batch_name="read-only")
        before_manifest = history_file.read_text(encoding="utf-8")

        read_latest_run(history_file)
        read_run_history_summary(history_file, limit=1)
        browse_run_history(history_file, limit=1)

        self.assertEqual(history_file.read_text(encoding="utf-8"), before_manifest)
        self.assertFalse((history_file.parent / "latest_run.json").exists())
        self.assertFalse((history_file.parent / "run_history_summary.json").exists())

    def test_browsing_missing_history_is_explicit(self) -> None:
        missing_history_file = self.temp_dir / "missing" / "run_history.jsonl"

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["history", "--history-file", str(missing_history_file), "--latest"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("no run history entries available", stderr.getvalue())

    def test_browsing_does_not_pollute_internal_schema(self) -> None:
        history_file = self._append_runs(["run-one"], batch_name="schema-clean")

        latest_payload = read_latest_run(history_file)
        summary_payload = read_run_history_summary(history_file, limit=1)

        latest_json = json.dumps(latest_payload, ensure_ascii=True)
        summary_json = json.dumps(summary_payload, ensure_ascii=True)
        self.assertNotIn("evaluation_input_bundle", latest_json)
        self.assertNotIn("realm_evaluation", summary_json)

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
