"""Extra coverage for runtime.executor uncovered branches.

Targets (per coverage report):
  line 20       - execute_step tool_name not in available tools
  lines 34-35   - run_tool raises exception, captured by execute_step
  lines 92-104  - run_tool 'run_command' branch
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from runtime.executor import Executor


class ExecutorRunCommandTests(unittest.TestCase):
    """Lines 92-104 — run_command stub tool."""

    def setUp(self) -> None:
        self.executor = Executor()
        self.tools = [
            {"name": "read_file"},
            {"name": "write_file"},
            {"name": "search_docs"},
            {"name": "run_command"},
        ]

    def test_run_command_returns_expected_schema(self) -> None:
        result = self.executor.run_tool("run_command", {"command": "ls -la"})
        self.assertEqual(result["output"]["exit_code"], 0)
        self.assertIn("ls -la", result["output"]["stdout"])
        self.assertIn("stub-command:", result["output"]["summary"])
        self.assertEqual(result["artifacts"], [])

    def test_run_command_with_empty_command(self) -> None:
        result = self.executor.run_tool("run_command", {})
        self.assertIn("stub-command:", result["output"]["summary"])
        self.assertEqual(result["output"]["exit_code"], 0)

    def test_execute_step_with_run_command_tool(self) -> None:
        step = {"tool_name": "run_command", "tool_input": {"command": "echo hello"}}
        result = self.executor.execute_step(step, self.tools, working_context=None)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["tool_name"], "run_command")
        self.assertIn("echo hello", result["output"]["stdout"])

    def test_unsupported_tool_raises_value_error(self) -> None:
        with self.assertRaises(ValueError, msg="unsupported tool"):
            self.executor.run_tool("teleport", {})


class ExecutorToolNotAvailableTests(unittest.TestCase):
    """Line 20 — tool_name not in available_tools."""

    def setUp(self) -> None:
        self.executor = Executor()

    def test_unknown_tool_returns_error_result(self) -> None:
        step = {"tool_name": "unknown_tool", "tool_input": {}}
        tools = [{"name": "read_file"}]
        result = self.executor.execute_step(step, tools, working_context=None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["type"], "tool_not_available")
        self.assertIn("unknown_tool", result["error"]["message"])

    def test_empty_tool_name_returns_error_result(self) -> None:
        step = {"tool_name": "", "tool_input": {}}
        tools = [{"name": "read_file"}]
        result = self.executor.execute_step(step, tools, working_context=None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["type"], "tool_not_available")


class ExecutorRunToolExceptionTests(unittest.TestCase):
    """Lines 34-35 — run_tool raises, execute_step catches it."""

    def test_run_tool_exception_is_captured_as_error_result(self) -> None:
        executor = Executor()
        tools = [{"name": "read_file"}]

        with patch.object(
            executor, "run_tool", side_effect=RuntimeError("tool exploded")
        ):
            step = {"tool_name": "read_file", "tool_input": {"path": "/tmp/x"}}
            result = executor.execute_step(step, tools, working_context=None)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["type"], "RuntimeError")
        self.assertIn("tool exploded", result["error"]["message"])
        self.assertIsNone(result["output"])


if __name__ == "__main__":
    unittest.main()
