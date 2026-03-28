from __future__ import annotations

from collections.abc import Mapping
import re


class Interviewer:
    """Ask only for the smallest set of clarifications needed to bound a task."""

    MAX_QUESTIONS = 3
    MISSING_INFO_THRESHOLD = 0
    VAGUE_TASK_PATTERNS = {
        "help",
        "do it",
        "fix it",
        "make it better",
        "something is wrong",
        "this",
    }
    ACTION_HINTS = {
        "implement",
        "fix",
        "review",
        "search",
        "plan",
        "design",
        "research",
        "analyze",
        "write",
        "build",
        "debug",
    }
    CONSTRAINT_HINTS = {
        "only",
        "must",
        "within",
        "without",
        "do not",
        "don't",
        "read-only",
        "no ",
    }
    SAFE_RISK_HINTS = {
        "search",
        "read",
        "summarize",
        "explain",
        "review",
        "inspect",
    }
    HIGH_RISK_HINTS = {
        "delete",
        "drop",
        "destroy",
        "production",
        "migrate",
        "irreversible",
    }

    def review(
        self,
        user_task: str,
        known_answers: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        task_text = user_task.strip()
        if not task_text:
            raise ValueError("user_task must not be empty")

        answers = dict(known_answers or {})
        clarified_constraints = self._extract_builder_constraints(answers)
        missing_fields: list[str] = []

        if self._goal_is_ambiguous(task_text):
            missing_fields.append("goal")
        if not self._success_criteria_is_clear(task_text, clarified_constraints):
            missing_fields.append("success_criteria")
        if not self._constraints_are_clear(task_text, clarified_constraints):
            missing_fields.append("key_constraints")
        if not self._risk_is_classifiable(task_text, clarified_constraints):
            missing_fields.append("risk_assessment")

        stop_conditions_met = len(missing_fields) <= self.MISSING_INFO_THRESHOLD
        should_continue = not stop_conditions_met
        questions = []
        if should_continue:
            questions = self._build_questions(missing_fields)[: self.MAX_QUESTIONS]

        stop_reason = (
            "minimum_information_satisfied"
            if stop_conditions_met
            else "clarification_required"
        )
        if should_continue and len(missing_fields) > self.MAX_QUESTIONS:
            stop_reason = "question_cap_applied"

        return {
            "should_continue": should_continue,
            "questions": questions,
            "missing_fields": missing_fields,
            "stop_conditions_met": stop_conditions_met,
            "stop_reason": stop_reason,
            "clarified_constraints": clarified_constraints,
        }

    def _extract_builder_constraints(self, answers: Mapping[str, object]) -> dict[str, object]:
        supported_keys = {
            "task_id",
            "success_criteria",
            "allowed_tools",
            "write_permission_level",
            "stop_conditions",
            "uncertainty_level",
            "residual_risk_level",
            "methodology_family",
            "failure_escalation_policy",
            "expected_artifacts",
        }
        return {
            key: value
            for key, value in answers.items()
            if key in supported_keys and value is not None
        }

    def _goal_is_ambiguous(self, task_text: str) -> bool:
        lowered = task_text.lower().strip()
        normalized = re.sub(r"\s+", " ", lowered)
        if normalized in self.VAGUE_TASK_PATTERNS:
            return True
        tokens = re.findall(r"[a-z0-9_]+", lowered)
        if len(tokens) < 2:
            return True
        return not any(token in self.ACTION_HINTS for token in tokens)

    def _success_criteria_is_clear(
        self,
        task_text: str,
        clarified_constraints: Mapping[str, object],
    ) -> bool:
        if clarified_constraints.get("success_criteria"):
            return True
        lowered = task_text.lower()
        return any(
            marker in lowered
            for marker in ("should", "must", "return", "produce", "pass", "output")
        ) or not self._goal_is_ambiguous(task_text)

    def _constraints_are_clear(
        self,
        task_text: str,
        clarified_constraints: Mapping[str, object],
    ) -> bool:
        if any(
            clarified_constraints.get(key)
            for key in ("allowed_tools", "write_permission_level", "stop_conditions")
        ):
            return True
        lowered = task_text.lower()
        return any(marker in lowered for marker in self.CONSTRAINT_HINTS)

    def _risk_is_classifiable(
        self,
        task_text: str,
        clarified_constraints: Mapping[str, object],
    ) -> bool:
        if clarified_constraints.get("uncertainty_level") or clarified_constraints.get(
            "residual_risk_level"
        ):
            return True
        lowered = task_text.lower()
        if any(token in lowered for token in self.HIGH_RISK_HINTS):
            return True
        if any(token in lowered for token in self.SAFE_RISK_HINTS):
            return True
        return not self._goal_is_ambiguous(task_text)

    def _build_questions(self, missing_fields: list[str]) -> list[str]:
        prompts = {
            "goal": "What exact outcome do you want this task to produce?",
            "success_criteria": "How should success be judged for this task?",
            "key_constraints": "What constraints must stay fixed, such as tools, permissions, or scope limits?",
            "risk_assessment": "Should this be treated as low-risk, or does it touch destructive, production, or irreversible behavior?",
        }
        return [prompts[field] for field in missing_fields if field in prompts]
