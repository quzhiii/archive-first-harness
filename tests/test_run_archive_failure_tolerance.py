from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.cli import load_settings, main
from entrypoints.task_runner import SurfaceTaskRequest, run_task_request


class RunArchiveFailureToleranceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_run_archive_failure_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_run_task_request_survives_archive_write_failure(self) -> None:
        with patch("entrypoints.task_runner.write_run_archive", side_effect=RuntimeError("archive failed")):
            result = run_task_request(
                SurfaceTaskRequest(task="Search docs for runtime context"),
                load_settings(),
            )

        self.assertEqual(result["execution_result"]["status"], "success")
        self.assertEqual(result["run_archive"]["status"], "failed")
        self.assertEqual(result["run_archive"]["error_type"], "RuntimeError")
        self.assertIn("archive failed", result["run_archive"]["message"])

    def test_cli_single_run_keeps_json_output_when_archive_write_fails(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with patch("entrypoints.task_runner.write_run_archive", side_effect=RuntimeError("archive failed")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["run", "Search", "docs", "for", "runtime", "context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(payload["run_archive"]["status"], "failed")
        self.assertEqual(payload["execution_result"]["status"], "success")


if __name__ == "__main__":
    unittest.main()
