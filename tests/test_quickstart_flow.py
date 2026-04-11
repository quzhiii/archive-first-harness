from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.quickstart_flow import ensure_repo_root_on_sys_path, run_quickstart


class QuickstartFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_quickstart_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.repo_root = Path(__file__).resolve().parents[1]

    def test_ensure_repo_root_on_sys_path_requires_entrypoints_directory(self) -> None:
        missing_root = self.temp_dir / "missing-root"
        missing_root.mkdir(parents=True, exist_ok=True)

        with self.assertRaises(FileNotFoundError):
            ensure_repo_root_on_sys_path(missing_root)

    def test_run_quickstart_prints_human_readable_first_run_path(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = run_quickstart(repo_root=self.repo_root)

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("archive-first-harness quickstart", output)
        self.assertIn("[1/3] inspect-state", output)
        self.assertIn('[2/3] run --task "ping" --task-type retrieval', output)
        self.assertIn("[3/3] archive --latest", output)
        self.assertIn("Latest archive", output)
        self.assertIn("raw run JSON is intentionally skipped", output)
        self.assertIn("python -m entrypoints.cli demo", output)
