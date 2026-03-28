from __future__ import annotations

from copy import deepcopy
import unittest

from planner.task_contract_builder import TaskContractBuilder
from runtime.verifier import Verifier


class VerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = TaskContractBuilder()
        self.verifier = Verifier()

    def test_verifies_normal_execution_result(self) -> None:
        contract = self.builder.build("Search docs for runtime context.")
        execution_result = {
            "status": "success",
            "tool_name": "search_docs",
            "output": {"matches": ["runtime"]},
            "error": None,
            "artifacts": [],
            "metadata": {"tool_input": {"query": "runtime"}},
        }

        report = self.verifier.verify_execution_result(execution_result, contract)

        self.assertTrue(report["passed"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["issues"], [])

    def test_missing_required_fields_fail_verification(self) -> None:
        contract = self.builder.build("Search docs for runtime context.")
        execution_result = {
            "status": "success",
            "tool_name": "search_docs",
            "output": {"matches": []},
            "error": None,
        }

        report = self.verifier.verify_execution_result(execution_result, contract)

        self.assertFalse(report["passed"])
        self.assertTrue(any(issue["code"] == "missing_field" for issue in report["issues"]))

    def test_consistency_check_emits_issues_and_warnings(self) -> None:
        contract = self.builder.build(
            "Implement a code patch for the runtime.",
            constraints={"expected_artifacts": ["code_patch"]},
        )
        execution_result = {
            "status": "success",
            "tool_name": "",
            "output": {"summary": "patched"},
            "error": {"type": "unexpected", "message": "should not be here"},
            "artifacts": [],
            "metadata": {},
        }

        report = self.verifier.verify_execution_result(execution_result, contract)

        self.assertTrue(any(issue["code"] == "success_with_error" for issue in report["issues"]))
        self.assertTrue(any(warning["code"] == "missing_tool_name" for warning in report["warnings"]))
        self.assertTrue(any(warning["code"] == "missing_expected_artifact" for warning in report["warnings"]))

    def test_verification_report_has_expected_shape(self) -> None:
        contract = self.builder.build("Search docs for runtime context.")
        execution_result = {
            "status": "error",
            "tool_name": "search_docs",
            "output": None,
            "error": {"type": "lookup_failed", "message": "stub failure"},
            "artifacts": [],
            "metadata": {},
        }

        report = self.verifier.verify_execution_result(execution_result, contract)

        self.assertIn("status", report)
        self.assertIn("passed", report)
        self.assertIn("issues", report)
        self.assertIn("warnings", report)
        self.assertIn("needs_followup", report)
        self.assertIn("residual_risk_hint", report)
        self.assertIn("metadata", report)

    def test_verifier_does_not_mutate_inputs(self) -> None:
        contract = self.builder.build("Search docs for runtime context.")
        execution_result = {
            "status": "success",
            "tool_name": "search_docs",
            "output": {"matches": ["runtime"]},
            "error": None,
            "artifacts": [],
            "metadata": {"tool_input": {"query": "runtime"}},
        }
        original = deepcopy(execution_result)

        self.verifier.verify_execution_result(execution_result, contract)

        self.assertEqual(execution_result, original)


if __name__ == "__main__":
    unittest.main()
