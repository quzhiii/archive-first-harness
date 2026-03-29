from __future__ import annotations

import unittest

from harness.contracts.profile_input_adapter import (
    ProfileInputResolution,
    resolve_surface_workflow_profile,
)
from harness.state.models import TaskType


class ProfileInputAdapterTests(unittest.TestCase):
    def test_precedence_prefers_workflow_profile_id(self) -> None:
        resolution = resolve_surface_workflow_profile(
            {
                "workflow_profile_id": "planning_design",
                "workflow_profile": "research_analysis",
                "mission_profile_id": "evaluation_regression",
            },
            task_type=TaskType.CODING,
        )

        self.assertIsInstance(resolution, ProfileInputResolution)
        self.assertEqual(resolution.workflow_profile_id, "planning_design")
        self.assertEqual(resolution.source, "workflow_profile_id")
        self.assertFalse(resolution.used_fallback)
        self.assertIsNone(resolution.fallback_reason)

    def test_known_alias_values_are_normalized_to_canonical_profile_ids(self) -> None:
        workflow_alias = resolve_surface_workflow_profile(
            {"workflow_profile": "Research-Analysis"},
            task_type=TaskType.RESEARCH,
        )
        mission_alias = resolve_surface_workflow_profile(
            {"mission_profile_id": "Evaluation Regression"},
            task_type=TaskType.REVIEW,
        )

        self.assertEqual(workflow_alias.workflow_profile_id, "research_analysis")
        self.assertEqual(workflow_alias.source, "workflow_profile")
        self.assertEqual(mission_alias.workflow_profile_id, "evaluation_regression")
        self.assertEqual(mission_alias.source, "mission_profile_id")

    def test_unknown_input_falls_back_to_task_type_default_when_available(self) -> None:
        resolution = resolve_surface_workflow_profile(
            {"workflow_profile": "unknown-profile"},
            task_type=TaskType.REVIEW,
        )

        self.assertEqual(resolution.workflow_profile_id, "evaluation_regression")
        self.assertEqual(resolution.source, "task_type_default")
        self.assertTrue(resolution.used_fallback)
        self.assertEqual(resolution.fallback_reason, "workflow_profile_unknown")

    def test_empty_input_falls_back_to_default_general_without_task_type(self) -> None:
        resolution = resolve_surface_workflow_profile(
            {"workflow_profile_id": "   "},
        )

        self.assertEqual(resolution.workflow_profile_id, "default_general")
        self.assertEqual(resolution.source, "default_general")
        self.assertTrue(resolution.used_fallback)
        self.assertEqual(resolution.fallback_reason, "workflow_profile_id_empty")

    def test_task_type_mapping_is_used_when_profile_is_not_provided(self) -> None:
        resolution = resolve_surface_workflow_profile({"task_type": "coding"})

        self.assertEqual(resolution.workflow_profile_id, "implementation_build")
        self.assertEqual(resolution.source, "task_type_default")
        self.assertTrue(resolution.used_fallback)
        self.assertEqual(resolution.fallback_reason, "profile_not_provided")


if __name__ == "__main__":
    unittest.main()
