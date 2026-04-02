from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.cli import load_settings
from entrypoints.run_archive import write_run_archive
from entrypoints.task_runner import SurfaceTaskRequest, run_task_request


class RunArchiveWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_run_archive_writer_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_writer_creates_archive_directory_and_expected_files(self) -> None:
        run_result = run_task_request(
            SurfaceTaskRequest(
                task="Search docs for runtime context",
                task_type="research",
            ),
            load_settings(),
        )

        archive_result = write_run_archive(
            archive_root=self.temp_dir / "manual-runs",
            run_id="run-one",
            run_result=run_result,
            created_at=datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc),
            surface_request={"task": "Search docs for runtime context"},
        )

        archive_dir = Path(archive_result["archive_dir"])
        self.assertTrue(archive_dir.exists())
        for name in (
            "manifest.json",
            "task_contract.json",
            "profile_and_mode.json",
            "verification_report.json",
            "metrics_summary.json",
            "evaluation_summary.json",
            "final_output.json",
            "context_plan.json",
            "execution_trace.jsonl",
            "failure_signature.json",
            "archive_index.json",
        ):
            self.assertTrue((archive_dir / name).exists(), name)

        manifest = json.loads((archive_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["run_id"], "run-one")
        self.assertEqual(manifest["status"], "success")
        self.assertEqual(manifest["archive_version"], "v1")
        self.assertEqual(manifest["workflow_profile_id"], run_result["surface"]["workflow_profile_id"])

    def test_writer_appends_global_archive_index(self) -> None:
        run_result = run_task_request(
            SurfaceTaskRequest(task="Search docs for runtime context"),
            load_settings(),
        )

        write_run_archive(
            archive_root=self.temp_dir / "manual-runs",
            run_id="run-a",
            run_result=run_result,
            surface_request={"task": "Search docs for runtime context"},
        )
        write_run_archive(
            archive_root=self.temp_dir / "manual-runs",
            run_id="run-b",
            run_result=run_result,
            surface_request={"task": "Search docs for runtime context"},
        )

        index_file = self.temp_dir / "manual-runs" / "index.jsonl"
        rows = [json.loads(line) for line in index_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual([row["run_id"] for row in rows], ["run-a", "run-b"])
        self.assertEqual(rows[0]["formation_id"], "default")
        self.assertEqual(rows[0]["policy_mode"], "default")


if __name__ == "__main__":
    unittest.main()

