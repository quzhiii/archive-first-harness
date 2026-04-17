"""Tests for user-defined WorkflowProfile loading from JSON file."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.contracts.workflow_profile import (
    BUILTIN_WORKFLOW_PROFILES,
    WorkflowProfile,
    load_profiles_from_file,
    resolve_workflow_profile_with_extras,
)


class TestLoadProfilesFromFile(unittest.TestCase):
    def _write_profile_file(self, tmp_dir: Path, data: dict) -> Path:
        p = tmp_dir / "profiles.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_missing_file_returns_empty(self):
        result = load_profiles_from_file("/nonexistent/path/profiles.json")
        self.assertEqual(result, {})

    def test_valid_file_loads_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_profile_file(
                Path(tmp),
                {
                    "paper_case_a": {
                        "name": "Paper Case A",
                        "intent_class": "build",
                        "success_focus": ["artifact correctness"],
                        "artifact_expectation": ["patch"],
                        "context_bias": ["task_block"],
                        "evaluation_bias": ["verification clarity"],
                    }
                },
            )
            profiles = load_profiles_from_file(p)
            self.assertIn("paper_case_a", profiles)
            self.assertEqual(profiles["paper_case_a"].intent_class, "build")

    def test_malformed_file_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text("not-json", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_profiles_from_file(p)

    def test_non_object_root_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "list.json"
            p.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_profiles_from_file(p)

    def test_builtin_profiles_unaffected(self):
        # loading a custom file must not mutate BUILTIN_WORKFLOW_PROFILES
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_profile_file(
                Path(tmp),
                {
                    "default_general": {  # same id as builtin
                        "name": "Override Attempt",
                        "intent_class": "custom",
                        "success_focus": [],
                        "artifact_expectation": [],
                        "context_bias": [],
                        "evaluation_bias": [],
                    }
                },
            )
            load_profiles_from_file(p)
            # builtin must be unchanged
            self.assertEqual(
                BUILTIN_WORKFLOW_PROFILES["default_general"].intent_class,
                "general",
            )

    def test_profile_fields_default_gracefully(self):
        """A minimal profile entry (only profile_id implied) should load without error."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_profile_file(Path(tmp), {"minimal_profile": {}})
            profiles = load_profiles_from_file(p)
            self.assertIn("minimal_profile", profiles)
            self.assertEqual(profiles["minimal_profile"].intent_class, "general")
            self.assertEqual(profiles["minimal_profile"].success_focus, ())


class TestResolveWithExtras(unittest.TestCase):
    def test_extra_profile_takes_precedence(self):
        custom = WorkflowProfile(
            profile_id="custom_x",
            name="Custom X",
            intent_class="custom",
            success_focus=(),
            artifact_expectation=(),
            context_bias=(),
            evaluation_bias=(),
        )
        result = resolve_workflow_profile_with_extras(
            "custom_x", extra_profiles={"custom_x": custom}
        )
        self.assertEqual(result.intent_class, "custom")

    def test_falls_back_to_builtin_when_not_in_extras(self):
        result = resolve_workflow_profile_with_extras(
            "research_analysis",
            extra_profiles={"other": None},  # type: ignore[dict-item]
        )
        self.assertEqual(result.profile_id, "research_analysis")

    def test_none_extras_falls_back_normally(self):
        result = resolve_workflow_profile_with_extras("research_analysis")
        self.assertEqual(result.profile_id, "research_analysis")

    def test_none_profile_id_with_extras_falls_back_to_default(self):
        result = resolve_workflow_profile_with_extras(None, extra_profiles={"x": None})  # type: ignore[dict-item]
        self.assertEqual(result.profile_id, "default_general")


if __name__ == "__main__":
    unittest.main()
