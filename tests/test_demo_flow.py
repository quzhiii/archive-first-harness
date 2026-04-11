from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.archive_browse import browse_run_archives, compare_run_archives
from entrypoints.cli import load_settings, main
from entrypoints.demo_flow import (
    DEMO_FAILURE_RUN_ID,
    DEMO_SUCCESS_RUN_ID,
    ensure_demo_archives,
)


class DemoFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_archive_demo_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_ensure_demo_archives_creates_deterministic_compare_pair(self) -> None:
        payload = ensure_demo_archives(load_settings())

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["success_run_id"], DEMO_SUCCESS_RUN_ID)
        self.assertEqual(payload["failure_run_id"], DEMO_FAILURE_RUN_ID)
        self.assertEqual(
            set(payload["created_run_ids"]), {DEMO_SUCCESS_RUN_ID, DEMO_FAILURE_RUN_ID}
        )

        browse_payload = browse_run_archives(
            self.temp_dir / "runs", task_type="demo", limit=10
        )
        run_ids = [item["run_id"] for item in browse_payload["entries"]]
        self.assertEqual(run_ids, [DEMO_SUCCESS_RUN_ID, DEMO_FAILURE_RUN_ID])

        comparison = compare_run_archives(
            self.temp_dir / "runs", DEMO_SUCCESS_RUN_ID, DEMO_FAILURE_RUN_ID
        )
        self.assertEqual(comparison["left"]["run_id"], DEMO_SUCCESS_RUN_ID)
        self.assertEqual(comparison["right"]["run_id"], DEMO_FAILURE_RUN_ID)
        self.assertEqual(comparison["left"]["status"], "success")
        self.assertEqual(comparison["right"]["status"], "failed")

    def test_demo_command_is_idempotent_and_human_readable(self) -> None:
        ensure_demo_archives(load_settings())

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["demo"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Demo archives ready", output)
        self.assertIn(f"success_run_id: {DEMO_SUCCESS_RUN_ID}", output)
        self.assertIn(f"failure_run_id: {DEMO_FAILURE_RUN_ID}", output)
        self.assertIn("deterministic demo archives", output)
        self.assertNotIn("{", output)
