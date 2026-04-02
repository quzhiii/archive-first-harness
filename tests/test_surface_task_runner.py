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
from harness.contracts.profile_input_adapter import ProfileInputResolution


class FailingExecutor:
    def execute_step(self, step, available_tools, working_context):
        return {
            "status": "error",
            "tool_name": step.get("tool_name"),
            "output": None,
            "error": {
                "type": "surface_execution_failure",
                "message": "forced failure for surface task runner test",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


class SurfaceTaskRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_surface_runner_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_surface_request_runs_with_minimal_and_optional_fields(self) -> None:
        result = run_task_request(
            SurfaceTaskRequest(
                task="Review runtime profile drift",
                task_type="review",
                success_criteria=["Return a focused review outcome."],
                expected_artifacts=["report"],
            ),
            load_settings(),
        )

        self.assertEqual(result["task_contract"]["task_type"], "review")
        self.assertEqual(result["task_contract"]["success_criteria"], ["Return a focused review outcome."])
        self.assertEqual(result["task_contract"]["expected_artifacts"], ["report"])
        self.assertEqual(result["surface"]["workflow_profile_id"], "evaluation_regression")

    def test_surface_runner_uses_shared_profile_input_adapter(self) -> None:
        with patch("entrypoints.task_runner.resolve_surface_workflow_profile") as resolve_mock:
            resolve_mock.return_value = ProfileInputResolution(
                workflow_profile_id="planning_design",
                source="workflow_profile",
                used_fallback=False,
                fallback_reason=None,
            )

            result = run_task_request(
                SurfaceTaskRequest(
                    task="Design a runtime harness plan",
                    workflow_profile="planning-design",
                ),
                load_settings(),
            )

        resolve_mock.assert_called_once()
        self.assertEqual(result["surface"]["profile_resolution"]["source"], "workflow_profile")
        self.assertEqual(result["task_contract"]["workflow_profile_id"], "planning_design")

    def test_known_profile_input_enters_runtime_consistently(self) -> None:
        result = run_task_request(
            SurfaceTaskRequest(
                task="Review runtime regression output",
                task_type="review",
                workflow_profile="Evaluation Regression",
            ),
            load_settings(),
        )

        self.assertEqual(result["task_contract"]["workflow_profile_id"], "evaluation_regression")
        self.assertEqual(
            result["evaluation_input_bundle"]["task_contract_summary"]["workflow_profile_id"],
            "evaluation_regression",
        )
        self.assertEqual(result["realm_evaluation"]["metadata"]["workflow_profile_id"], "evaluation_regression")

    def test_unknown_profile_fallback_is_consistent_between_function_and_cli(self) -> None:
        function_result = run_task_request(
            SurfaceTaskRequest(
                task="Review runtime regression output",
                task_type="review",
                workflow_profile="unknown-profile",
            ),
            load_settings(),
        )

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                [
                    "run",
                    "--task",
                    "Review runtime regression output",
                    "--task-type",
                    "review",
                    "--workflow-profile",
                    "unknown-profile",
                ]
            )

        cli_result = json.loads(stdout.getvalue())
        self.assertIn(exit_code, {0, 1})
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(function_result["surface"]["workflow_profile_id"], "evaluation_regression")
        self.assertEqual(cli_result["surface"]["workflow_profile_id"], "evaluation_regression")
        self.assertEqual(
            function_result["surface"]["profile_resolution"]["fallback_reason"],
            "workflow_profile_unknown",
        )
        self.assertEqual(
            cli_result["surface"]["profile_resolution"]["fallback_reason"],
            "workflow_profile_unknown",
        )

    def test_surface_output_keeps_runtime_schema_with_small_wrapper(self) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task="Search docs for runtime context"),
            load_settings(),
        )

        self.assertIn("execution_result", result)
        self.assertIn("verification_report", result)
        self.assertIn("evaluation_input_bundle", result)
        self.assertIn("realm_evaluation", result)
        self.assertIn("metrics_summary", result)
        self.assertIn("surface", result)
        self.assertEqual(sorted(result["surface"].keys()), ["profile_resolution", "workflow_profile_id"])
        self.assertEqual(result["telemetry"], result["metrics_summary"])
        self.assertEqual(result["evaluation"], result["realm_evaluation"])

    def test_coding_task_prefers_write_path_and_produces_code_patch_artifact(self) -> None:
        result = run_task_request(
            SurfaceTaskRequest(task="Implement a tiny archive marker file", task_type="coding"),
            load_settings(),
        )

        self.assertEqual(result["execution_result"]["tool_name"], "write_file")
        self.assertEqual(
            result["execution_result"]["artifacts"],
            [{"type": "file_change", "path": "artifacts/output.txt"}],
        )
        self.assertFalse(
            any(
                warning.get("code") == "missing_expected_artifact"
                for warning in result["verification_report"]["warnings"]
            )
        )

    def test_surface_does_not_introduce_control_semantics_on_failure(self) -> None:
        result = run_task_request(
            SurfaceTaskRequest(
                task="Review runtime regression output",
                task_type="review",
                workflow_profile_id="evaluation_regression",
            ),
            load_settings(),
            executor=FailingExecutor(),
        )

        self.assertEqual(result["execution_result"]["status"], "error")
        self.assertEqual(result["realm_evaluation"]["metadata"]["automatic_action"], "none")
        self.assertEqual(result["residual_followup"]["auto_execution"], "none")
        self.assertTrue(result["realm_evaluation"]["requires_human_review"])


if __name__ == "__main__":
    unittest.main()
