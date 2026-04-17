"""Extra coverage for entrypoints.batch_runner uncovered branches.

Targets (per coverage report):
  line 25  - stop_on_error type validation
  line 27  - empty tasks validation
  lines 62-64 - exception path in run_batch_request
  lines 109/115/118 - load_batch_request_file .json non-sequence / bad mapping
  lines 128-143 - load_batch_request_file .jsonl path
  lines 152-160 - _coerce_surface_batch_request mapping path
  line 177     - _extract_task_label fallback index label
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch
from uuid import uuid4

from entrypoints.batch_runner import (
    SurfaceBatchRequest,
    _coerce_surface_batch_request,
    _extract_task_label,
    load_batch_request_file,
    run_batch_request,
)
from entrypoints.cli import load_settings
from entrypoints.task_runner import SurfaceTaskRequest


class SurfaceBatchRequestValidationTests(unittest.TestCase):
    """Lines 25, 27 — __post_init__ validation."""

    def test_stop_on_error_must_be_bool(self) -> None:
        with self.assertRaises(TypeError):
            SurfaceBatchRequest(
                tasks=[SurfaceTaskRequest(task="t")],
                stop_on_error="yes",  # type: ignore[arg-type]
            )

    def test_empty_tasks_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            SurfaceBatchRequest(tasks=[])


class RunBatchRequestExceptionPathTests(unittest.TestCase):
    """Lines 62-64 — task_runner raises an exception mid-batch."""

    def test_exception_in_task_runner_is_recorded_as_failed(self) -> None:
        def boom(req, settings):
            raise RuntimeError("simulated runner failure")

        result = run_batch_request(
            SurfaceBatchRequest(tasks=[SurfaceTaskRequest(task="boom")]),
            load_settings(),
            task_runner=boom,
        )

        self.assertEqual(result["failed_tasks"], 1)
        self.assertEqual(result["completed_tasks"], 0)
        entry = result["results"][0]
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(entry["error"]["type"], "RuntimeError")
        self.assertIn("simulated runner failure", entry["error"]["message"])

    def test_exception_does_not_stop_batch_when_stop_on_error_false(self) -> None:
        calls: list[int] = []

        def sometimes_boom(req, settings):
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("first task explodes")
            return {
                "execution_result": {"status": "success"},
                "verification_report": {"passed": True, "status": "passed"},
                "surface": {
                    "workflow_profile_id": "default_general",
                    "profile_resolution": {
                        "workflow_profile_id": "default_general",
                        "source": "workflow_profile_id",
                        "used_fallback": False,
                        "fallback_reason": None,
                    },
                },
                "evaluation_input_bundle": {
                    "task_contract_summary": {"workflow_profile_id": "default_general"}
                },
                "realm_evaluation": {
                    "metadata": {
                        "automatic_action": "none",
                        "workflow_profile_id": "default_general",
                    },
                    "requires_human_review": False,
                },
                "metrics_summary": {"event_count": 1, "metric_count": 1, "metrics": {}},
            }

        result = run_batch_request(
            SurfaceBatchRequest(
                tasks=[SurfaceTaskRequest(task="t1"), SurfaceTaskRequest(task="t2")],
                stop_on_error=False,
            ),
            load_settings(),
            task_runner=sometimes_boom,
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(result["failed_tasks"], 1)
        self.assertEqual(result["completed_tasks"], 1)
        self.assertFalse(result["stopped_early"])


class LoadBatchRequestFileTests(unittest.TestCase):
    """Lines 109/115/118/128-143 — file loading branches."""

    def setUp(self) -> None:
        self.tmp = Path("tests") / f"_tmp_load_{uuid4().hex}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.tmp, ignore_errors=True))

    # --- .json branches ---

    def test_json_non_sequence_non_mapping_raises_type_error(self) -> None:
        p = self.tmp / "bad.json"
        p.write_text(json.dumps("just a string"), encoding="utf-8")
        with self.assertRaises(TypeError):
            load_batch_request_file(p)

    def test_json_mapping_without_tasks_raises_type_error(self) -> None:
        p = self.tmp / "no_tasks.json"
        p.write_text(json.dumps({"batch_name": "x"}), encoding="utf-8")
        with self.assertRaises(TypeError):
            load_batch_request_file(p)

    def test_json_mapping_with_tasks_as_string_raises_type_error(self) -> None:
        p = self.tmp / "bad_tasks.json"
        p.write_text(json.dumps({"tasks": "not-a-list"}), encoding="utf-8")
        with self.assertRaises(TypeError):
            load_batch_request_file(p)

    def test_json_mapping_with_metadata_is_loaded(self) -> None:
        p = self.tmp / "with_meta.json"
        payload = {
            "batch_name": "meta-test",
            "tasks": [{"task": "do something"}],
            "metadata": {"env": "ci"},
            "stop_on_error": True,
        }
        p.write_text(json.dumps(payload), encoding="utf-8")
        req = load_batch_request_file(p)
        self.assertEqual(req.batch_name, "meta-test")
        self.assertTrue(req.stop_on_error)
        self.assertEqual(req.metadata, {"env": "ci"})

    # --- .jsonl branches ---

    def test_jsonl_loads_multiple_tasks(self) -> None:
        p = self.tmp / "tasks.jsonl"
        lines = [
            json.dumps({"task": "first"}),
            "",  # blank line should be skipped
            json.dumps({"task": "second"}),
        ]
        p.write_text("\n".join(lines), encoding="utf-8")
        req = load_batch_request_file(p)
        self.assertEqual(len(req.tasks), 2)
        self.assertEqual(req.batch_name, "tasks")  # stem of file

    def test_jsonl_non_mapping_line_raises_type_error(self) -> None:
        p = self.tmp / "bad.jsonl"
        p.write_text(json.dumps(["list", "not", "mapping"]) + "\n", encoding="utf-8")
        with self.assertRaises(TypeError):
            load_batch_request_file(p)

    def test_jsonl_respects_stop_on_error_override(self) -> None:
        p = self.tmp / "override.jsonl"
        p.write_text(json.dumps({"task": "t"}) + "\n", encoding="utf-8")
        req = load_batch_request_file(p, stop_on_error=True)
        self.assertTrue(req.stop_on_error)

    def test_unsupported_extension_raises_value_error(self) -> None:
        p = self.tmp / "tasks.csv"
        p.write_text("task,type\ndo it,general", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_batch_request_file(p)


class CoerceSurfaceBatchRequestTests(unittest.TestCase):
    """Lines 152-160 — _coerce_surface_batch_request mapping path."""

    def test_mapping_is_coerced_to_surface_batch_request(self) -> None:
        raw = {
            "tasks": [{"task": "task from mapping"}],
            "batch_name": "coerced",
            "stop_on_error": True,
            "metadata": {"source": "mapping"},
        }
        result = _coerce_surface_batch_request(raw)
        self.assertIsInstance(result, SurfaceBatchRequest)
        self.assertEqual(result.batch_name, "coerced")
        self.assertTrue(result.stop_on_error)
        self.assertEqual(result.metadata, {"source": "mapping"})

    def test_mapping_without_tasks_sequence_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            _coerce_surface_batch_request({"tasks": "not-a-list"})

    def test_non_mapping_non_batch_request_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            _coerce_surface_batch_request(["list"])  # type: ignore[arg-type]


class ExtractTaskLabelTests(unittest.TestCase):
    """Line 177 — _extract_task_label index fallback."""

    def test_mapping_with_no_task_key_falls_back_to_index(self) -> None:
        label = _extract_task_label({"description": "no task key here"}, index=3)
        self.assertEqual(label, "task-3")

    def test_mapping_with_blank_task_falls_back_to_index(self) -> None:
        label = _extract_task_label({"task": "   "}, index=7)
        self.assertEqual(label, "task-7")

    def test_surface_task_request_returns_task_text(self) -> None:
        req = SurfaceTaskRequest(task="my task")
        label = _extract_task_label(req, index=0)
        self.assertEqual(label, "my task")


if __name__ == "__main__":
    unittest.main()
