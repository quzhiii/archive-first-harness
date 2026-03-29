from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest
from unittest.mock import patch

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


class BatchTaskRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_batch_runner_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.env_patch = patch.dict(
            "os.environ",
            {"AI_HARNESS_ARTIFACTS_DIR": str(self.temp_dir)},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_batch_request_constructs_with_minimal_fields(self) -> None:
        request = SurfaceBatchRequest(
            tasks=[SurfaceTaskRequest(task="Search docs for runtime context")],
            batch_name="smoke-batch",
        )

        self.assertEqual(request.batch_name, "smoke-batch")
        self.assertFalse(request.stop_on_error)
        self.assertEqual(len(request.tasks), 1)

    def test_batch_runner_reuses_single_task_entry(self) -> None:
        requests = [
            SurfaceTaskRequest(task="Task one"),
            {"task": "Task two", "workflow_profile": "planning design"},
        ]
        with patch("entrypoints.batch_runner.run_task_request") as task_runner_mock:
            task_runner_mock.side_effect = [
                _surface_result(status="success"),
                _surface_result(status="success", profile_id="planning_design"),
            ]
            result = run_batch_request(
                SurfaceBatchRequest(tasks=requests, batch_name="reuse-check"),
                load_settings(),
            )

        self.assertEqual(task_runner_mock.call_count, 2)
        self.assertEqual(result["completed_tasks"], 2)
        self.assertEqual(result["failed_tasks"], 0)

    def test_default_failure_policy_continues_after_error(self) -> None:
        with patch("entrypoints.batch_runner.run_task_request") as task_runner_mock:
            task_runner_mock.side_effect = [
                _surface_result(status="success"),
                _surface_result(status="error"),
                _surface_result(status="success"),
            ]
            result = run_batch_request(
                SurfaceBatchRequest(
                    tasks=[
                        SurfaceTaskRequest(task="Task one"),
                        SurfaceTaskRequest(task="Task two"),
                        SurfaceTaskRequest(task="Task three"),
                    ],
                ),
                load_settings(),
            )

        self.assertEqual(task_runner_mock.call_count, 3)
        self.assertEqual(result["completed_tasks"], 2)
        self.assertEqual(result["failed_tasks"], 1)
        self.assertFalse(result["stopped_early"])
        self.assertEqual([item["status"] for item in result["results"]], ["completed", "failed", "completed"])

    def test_stop_on_error_stops_batch_early(self) -> None:
        with patch("entrypoints.batch_runner.run_task_request") as task_runner_mock:
            task_runner_mock.side_effect = [
                _surface_result(status="success"),
                _surface_result(status="error"),
                _surface_result(status="success"),
            ]
            result = run_batch_request(
                SurfaceBatchRequest(
                    tasks=[
                        SurfaceTaskRequest(task="Task one"),
                        SurfaceTaskRequest(task="Task two"),
                        SurfaceTaskRequest(task="Task three"),
                    ],
                    stop_on_error=True,
                ),
                load_settings(),
            )

        self.assertEqual(task_runner_mock.call_count, 2)
        self.assertEqual(result["completed_tasks"], 1)
        self.assertEqual(result["failed_tasks"], 1)
        self.assertTrue(result["stopped_early"])
        self.assertEqual(len(result["results"]), 2)

    def test_batch_output_schema_stays_small_and_aggregated(self) -> None:
        result = run_batch_request(
            SurfaceBatchRequest(
                tasks=[
                    SurfaceTaskRequest(task="Search docs for runtime context"),
                    SurfaceTaskRequest(task="Review runtime regression output", task_type="review"),
                ],
                batch_name="schema-check",
            ),
            load_settings(),
        )

        self.assertEqual(
            sorted(result.keys()),
            ["batch_name", "completed_tasks", "failed_tasks", "results", "stopped_early", "summary", "total_tasks"],
        )
        self.assertEqual(result["batch_name"], "schema-check")
        self.assertEqual(result["total_tasks"], 2)
        self.assertEqual(len(result["results"]), 2)
        self.assertIn("result", result["results"][0])
        self.assertIn("execution_result", result["results"][0]["result"])
        self.assertNotIn("evaluation_input_bundle", result)

    def test_cli_batch_file_uses_same_profile_fallback_as_function_entry(self) -> None:
        batch_path = self.temp_dir / "batch.json"
        batch_payload = {
            "batch_name": "cli-batch",
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

        function_result = run_batch_request(load_batch_request_file(batch_path), load_settings())

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["run", "--batch-file", str(batch_path)])

        cli_result = json.loads(stdout.getvalue())
        self.assertIn(exit_code, {0, 1})
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(function_result["results"][0]["result"]["surface"]["workflow_profile_id"], "evaluation_regression")
        self.assertEqual(cli_result["results"][0]["result"]["surface"]["workflow_profile_id"], "evaluation_regression")
        self.assertEqual(cli_result["results"][1]["result"]["surface"]["workflow_profile_id"], "planning_design")

    def test_batch_does_not_mutate_following_task_inputs_or_add_control_logic(self) -> None:
        observed_tasks: list[object] = []

        def fake_task_runner(task_request, settings):
            observed_tasks.append(task_request)
            if len(observed_tasks) == 1:
                return _surface_result(status="error")
            return _surface_result(status="success", profile_id="planning_design")

        second_task = {"task": "Design runtime harness plan", "workflow_profile": "planning design"}
        result = run_batch_request(
            SurfaceBatchRequest(
                tasks=[
                    {"task": "Review runtime regression output", "task_type": "review"},
                    second_task,
                ],
                stop_on_error=False,
            ),
            load_settings(),
            task_runner=fake_task_runner,
        )

        self.assertEqual(len(observed_tasks), 2)
        self.assertEqual(observed_tasks[1], second_task)
        self.assertFalse(result["stopped_early"])
        self.assertEqual(result["results"][0]["status"], "failed")
        self.assertEqual(result["results"][1]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
