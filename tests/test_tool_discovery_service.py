from __future__ import annotations

import unittest

from harness.tools.tool_discovery_service import ToolDiscoveryService


class ToolDiscoveryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ToolDiscoveryService()

    def test_list_candidate_tools_returns_small_signature_list(self) -> None:
        candidates = self.service.list_candidate_tools("coding")

        self.assertGreater(len(candidates), 0)
        self.assertTrue(all("name" in tool for tool in candidates))
        self.assertTrue(all("signature" in tool for tool in candidates))

    def test_candidate_tools_do_not_include_full_schema_by_default(self) -> None:
        candidates = self.service.list_candidate_tools("coding")

        self.assertTrue(all("schema" not in tool for tool in candidates))

    def test_get_tool_signature_by_name(self) -> None:
        signature = self.service.get_tool_signature("read_file")

        self.assertEqual(signature["name"], "read_file")
        self.assertIn("path", signature["signature"]["input"])

    def test_get_tool_schema_by_name(self) -> None:
        schema = self.service.get_tool_schema("write_file")

        self.assertEqual(schema["name"], "write_file")
        self.assertEqual(schema["schema"]["type"], "object")
        self.assertIn("content", schema["schema"]["properties"])

    def test_allowed_tools_limits_candidate_range(self) -> None:
        candidates = self.service.list_candidate_tools(
            "coding",
            allowed_tools=["run_tests"],
        )

        self.assertEqual([tool["name"] for tool in candidates], ["run_command"])

    def test_cleanup_tool_context_returns_explicit_result(self) -> None:
        result = self.service.cleanup_tool_context("search_docs")

        self.assertEqual(
            result,
            {
                "tool_name": "search_docs",
                "status": "cleaned",
                "removed_context": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
