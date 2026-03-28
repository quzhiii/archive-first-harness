from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

from entrypoints.cli import load_settings, main, run_command


class FailingExecutor:
    def execute_step(self, step, available_tools, working_context):
        return {
            "status": "error",
            "tool_name": step.get("tool_name"),
            "output": None,
            "error": {
                "type": "stubbed_execution_failure",
                "message": "forced failure for integration smoke test",
            },
            "artifacts": [],
            "metadata": {
                "tool_input": dict(step.get("tool_input") or {}),
                "available_tool_count": len(available_tools),
                "task_note_count": len(getattr(working_context, "selected_task_notes", [])),
            },
        }


class IntegrationSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_integration_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_scenario_a_minimal_success_path(self) -> None:
        result = run_command("Search docs for runtime context", load_settings())

        self.assertTrue(result["task_contract"]["contract_id"])
        self.assertEqual(result["execution_result"]["status"], "success")
        self.assertEqual(result["verification_report"]["status"], "passed")
        self.assertGreater(len(result["candidate_tools"]), 0)
        self.assertGreater(result["working_context_summary"]["task_note_count"], 0)
        self.assertGreaterEqual(result["telemetry"]["event_count"], 2)
        self.assertEqual(result["evaluation"]["recommendation"], "keep")
        self.assertIn("verifier_handoff", result)

    def test_scenario_b_sparse_input_falls_back_to_conservative_defaults(self) -> None:
        result = run_command("help", load_settings())
        contract = result["task_contract"]

        self.assertEqual(contract["task_type"], "generation")
        self.assertEqual(contract["schema_version"], "v1")
        self.assertTrue(contract["success_criteria"])
        self.assertTrue(contract["allowed_tools"])
        self.assertTrue(contract["stop_conditions"])
        self.assertTrue(contract["expected_artifacts"])
        self.assertTrue(contract["token_budget"])
        self.assertTrue(contract["latency_budget"])
        self.assertIn(result["execution_result"]["status"], {"success", "error"})
        self.assertNotEqual(result["verification_report"]["status"], "")

    def test_scenario_c_execution_failure_is_structured_and_visible(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with patch("entrypoints.cli.Executor", FailingExecutor):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["run", "Search", "docs", "for", "runtime", "context"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["execution_result"]["status"], "error")
        self.assertEqual(payload["execution_result"]["error"]["type"], "stubbed_execution_failure")
        self.assertEqual(payload["verification_report"]["status"], "failed")
        self.assertTrue(any(issue["code"] == "execution_failed" for issue in payload["verification_report"]["issues"]))
        self.assertIn("execution_failure_count", payload["telemetry"]["metrics"])
        self.assertNotEqual(payload["evaluation"]["recommendation"], "keep")
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
