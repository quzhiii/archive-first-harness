from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.cli import main


class CliSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_cli_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_run_command_executes_minimal_main_path(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["run", "Search", "docs", "for", "runtime", "context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["execution_result"]["status"], "success")
        self.assertIn("verification_report", payload)
        self.assertIn("evaluation", payload)
        self.assertEqual(stderr.getvalue(), "")

    def test_inspect_state_is_callable_and_clear(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["inspect-state"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("state_files", payload)
        self.assertEqual(stderr.getvalue(), "")

    def test_inspect_contract_is_callable_and_clear(self) -> None:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            main(["run", "Search", "docs"])

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["inspect-contract"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("contract", payload)
        self.assertEqual(stderr.getvalue(), "")

    def test_cli_errors_do_not_fail_silently(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["inspect-contract"])

        self.assertEqual(exit_code, 1)
        self.assertIn("CLI error:", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")

    def test_cli_does_not_require_interactive_flow(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["run", "Implement", "runtime", "entrypoint"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertTrue(stdout.getvalue().strip().startswith("{"))


if __name__ == "__main__":
    unittest.main()
