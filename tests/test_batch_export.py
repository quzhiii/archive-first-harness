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
from entrypoints.batch_runner import SurfaceBatchRequest, load_batch_request_file, run_batch_request
from entrypoints.cli import load_settings, main
from entrypoints.task_runner import SurfaceTaskRequest



def _surface_result(*, status: str, profile_id: str = "default_general") -> dict[str, object]:
    passed = status == "success"
    return {
        "execution_result": {"status": status},
        "verification_report": {"passed": passed, "status": "passed" if passed else "failed"},
        "surface": {
            "workflow_profile_id": profile_id,
            "profile_resolution": {
                "workflow_profile_id": profile_id,
                "source": "workflow_profile_id",
                "used_fallback": False,
                "fallback_reason": None,
            },
        },
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": profile_id,
            }
        },
        "realm_evaluation": {
            "metadata": {"automatic_action": "none", "workflow_profile_id": profile_id},
            "requires_human_review": not passed,
        },
        "metrics_summary": {"event_count": 1, "metric_count": 1, "metrics": {}},
    }


class BatchExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_batch_export_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_export_options_construct_with_minimal_output_dir(self) -> None:
        options = BatchExportOptions(output_dir=self.temp_dir / "exports")

        self.assertTrue(options.write_json)
        self.assertTrue(options.write_jsonl)
        self.assertTrue(options.write_markdown_summary)
        self.assertIsNone(options.base_name)

    def test_json_export_writes_stable_snapshot(self) -> None:
        batch_result = self._sample_batch_result(batch_name="json-export")
        original = deepcopy(batch_result)

        export_result = export_batch_results(
            batch_result,
            BatchExportOptions(
                output_dir=self.temp_dir / "json-export",
                write_json=True,
                write_jsonl=False,
                write_markdown_summary=False,
            ),
        )

        json_path = Path(export_result["written_files"][0]["path"])
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(export_result["exported_formats"], ["json"])
        self.assertEqual(payload["batch_name"], "json-export")
        self.assertEqual(sorted(payload.keys()), sorted(batch_result.keys()))
        self.assertEqual(batch_result, original)

    def test_jsonl_export_writes_one_task_per_line(self) -> None:
        batch_result = self._sample_batch_result(batch_name="jsonl-export")

        export_result = export_batch_results(
            batch_result,
            BatchExportOptions(
                output_dir=self.temp_dir / "jsonl-export",
                write_json=False,
                write_jsonl=True,
                write_markdown_summary=False,
            ),
        )

        jsonl_path = Path(export_result["written_files"][0]["path"])
        rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(rows), batch_result["total_tasks"])
        self.assertEqual(
            sorted(rows[0].keys()),
            [
                "error_type",
                "execution_status",
                "status",
                "task",
                "task_index",
                "verification_passed",
                "workflow_profile_id",
            ],
        )
        self.assertEqual(rows[1]["workflow_profile_id"], "evaluation_regression")

    def test_markdown_summary_is_minimal_and_readable(self) -> None:
        batch_result = {
            "batch_name": "failure-batch",
            "total_tasks": 2,
            "completed_tasks": 1,
            "failed_tasks": 1,
            "stopped_early": False,
            "summary": "Batch 'failure-batch' processed 2/2 tasks; 1 completed, 1 failed.",
            "results": [
                {
                    "task_index": 0,
                    "task": "Search docs for runtime context",
                    "status": "completed",
                    "result": _surface_result(status="success"),
                },
                {
                    "task_index": 1,
                    "task": "Review runtime regression output",
                    "status": "failed",
                    "result": _surface_result(status="error", profile_id="evaluation_regression"),
                },
            ],
        }

        export_result = export_batch_results(
            batch_result,
            BatchExportOptions(
                output_dir=self.temp_dir / "md-export",
                write_json=False,
                write_jsonl=False,
                write_markdown_summary=True,
            ),
        )

        markdown_path = Path(export_result["written_files"][0]["path"])
        markdown = markdown_path.read_text(encoding="utf-8")
        self.assertIn("# Batch Summary: failure-batch", markdown)
        self.assertIn("- Total tasks: 2", markdown)
        self.assertIn("## Tasks", markdown)
        self.assertIn("`failed` `evaluation_regression` Review runtime regression output", markdown)
        self.assertIn("## Failures", markdown)
        self.assertNotIn("evaluation_input_bundle", markdown)
        self.assertNotIn("metrics_summary", markdown)

    def test_cli_output_dir_uses_same_batch_result_and_default_export_set(self) -> None:
        batch_path = self.temp_dir / "batch.json"
        batch_payload = {
            "batch_name": "cli-export",
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

        function_batch_result = run_batch_request(load_batch_request_file(batch_path), load_settings())

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main([
                "run",
                "--batch-file",
                str(batch_path),
                "--output-dir",
                str(self.temp_dir / "cli-exports"),
            ])

        cli_result = json.loads(stdout.getvalue())
        self.assertIn(exit_code, {0, 1})
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(cli_result["artifacts_export"]["exported_formats"], ["json", "jsonl", "markdown"])
        self.assertEqual(
            cli_result["results"][0]["result"]["surface"]["workflow_profile_id"],
            function_batch_result["results"][0]["result"]["surface"]["workflow_profile_id"],
        )
        for item in cli_result["artifacts_export"]["written_files"]:
            self.assertTrue(Path(item["path"]).exists())

    def test_export_does_not_mutate_batch_result_or_internal_schema(self) -> None:
        batch_result = self._sample_batch_result(batch_name="no-mutation")
        original = deepcopy(batch_result)

        export_batch_results(batch_result, BatchExportOptions(output_dir=self.temp_dir / "no-mutation"))

        self.assertEqual(batch_result, original)
        self.assertNotIn("artifacts_export", batch_result)
        self.assertIn("evaluation_input_bundle", batch_result["results"][0]["result"])
        self.assertIn("realm_evaluation", batch_result["results"][0]["result"])

    def test_cli_export_flags_require_output_dir(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main([
                "run",
                "--batch-file",
                "tasks.json",
                "--export-json",
            ])

        self.assertEqual(exit_code, 1)
        self.assertIn("--output-dir", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")

    def _sample_batch_result(self, *, batch_name: str) -> dict[str, object]:
        return run_batch_request(
            SurfaceBatchRequest(
                tasks=[
                    SurfaceTaskRequest(task="Search docs for runtime context"),
                    SurfaceTaskRequest(task="Review runtime regression output", task_type="review"),
                ],
                batch_name=batch_name,
            ),
            load_settings(),
        )


if __name__ == "__main__":
    unittest.main()
