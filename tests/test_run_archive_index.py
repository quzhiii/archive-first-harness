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


class RunArchiveIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_run_archive_index_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_index_rows_keep_minimal_searchable_fields(self) -> None:
        run_result = run_task_request(
            SurfaceTaskRequest(task="Search docs for runtime context"),
            load_settings(),
        )

        write_run_archive(
            archive_root=self.temp_dir / "indexed-runs",
            run_id="run-one",
            run_result=run_result,
            created_at=datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc),
            surface_request={"task": "Search docs for runtime context"},
        )

        row = json.loads((self.temp_dir / "indexed-runs" / "index.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(
            sorted(row.keys()),
            [
                "archive_dir",
                "created_at",
                "failure_class",
                "formation_id",
                "policy_mode",
                "run_id",
                "status",
                "task_type",
                "workflow_profile_id",
            ],
        )
        self.assertEqual(row["run_id"], "run-one")
        self.assertEqual(row["task_type"], "retrieval")
        self.assertEqual(row["formation_id"], "default")
        self.assertEqual(row["policy_mode"], "default")


if __name__ == "__main__":
    unittest.main()
