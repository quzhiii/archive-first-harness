from __future__ import annotations

import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.cli import load_settings
from entrypoints.task_runner import SurfaceTaskRequest, run_task_request


class FailingExecutor:
    def execute_step(self, step, available_tools, working_context):
        return {
            "status": "error",
            "tool_name": step.get("tool_name"),
            "output": None,
            "error": {
                "type": "surface_execution_failure",
                "message": "forced failure for archive trace test",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


class RunArchiveTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_run_archive_trace_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_success_run_writes_trace_and_context_plan(self) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task="Search docs for runtime context"),
            load_settings(),
        )

        archive_dir = Path(result["run_archive"]["archive_dir"])
        context_plan = json.loads((archive_dir / "context_plan.json").read_text(encoding="utf-8"))
        trace_rows = [
            json.loads(line)
            for line in (archive_dir / "execution_trace.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        signature = json.loads((archive_dir / "failure_signature.json").read_text(encoding="utf-8"))

        self.assertEqual(context_plan["workflow_profile_id"], result["surface"]["workflow_profile_id"])
        self.assertTrue(any(row["event_type"] == "task_contract_built" for row in trace_rows))
        self.assertTrue(any(row["event_type"] == "runtime_completed" for row in trace_rows))
        self.assertTrue(any(row["event_type"] == "evaluation_completed" for row in trace_rows))
        self.assertEqual(signature["status"], "success")

    def test_failed_run_writes_failure_signature(self) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task="Review runtime regression output", task_type="review"),
            load_settings(),
            executor=FailingExecutor(),
        )

        archive_dir = Path(result["run_archive"]["archive_dir"])
        signature = json.loads((archive_dir / "failure_signature.json").read_text(encoding="utf-8"))
        trace_rows = [
            json.loads(line)
            for line in (archive_dir / "execution_trace.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertEqual(signature["failed_stage"], "execution")
        self.assertEqual(signature["failure_class"], "surface_execution_failure")
        self.assertTrue(any(row["status"] == "error" for row in trace_rows if row["event_type"] == "runtime_completed"))


if __name__ == "__main__":
    unittest.main()
