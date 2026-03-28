from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
import re

from harness.state.models import TaskContract, TaskBlock, WorkingContext
from harness.state.state_manager import StateSnapshot


class ContextEngine:
    """Assemble the smallest useful working context from structured state."""

    MAX_TASK_NOTES = 6
    MAX_PROJECT_NOTES = 3
    MAX_GLOBAL_NOTES = 3
    MAX_TOOL_RESULTS = 3
    MAX_JOURNAL_LESSONS = 2

    def build_working_context(
        self,
        task_contract: TaskContract,
        state_snapshot: StateSnapshot,
        distilled_summary: str | None = None,
        recent_tool_results: list[object] | None = None,
        journal_lessons: list[object] | None = None,
    ) -> WorkingContext:
        task_notes = self._build_task_notes(
            state_snapshot.task_block,
            distilled_summary=distilled_summary,
        )
        project_notes = self._build_project_notes(task_contract, state_snapshot)
        global_notes = self._build_global_notes(task_contract, state_snapshot)
        retrieval_packets = self.prune_stale_items(
            task_contract,
            state_snapshot,
            recent_tool_results=recent_tool_results or [],
        )
        retrieval_packets.extend(self._build_journal_packets(journal_lessons or []))

        return WorkingContext(
            task_contract=task_contract,
            selected_global_notes=global_notes,
            selected_project_notes=project_notes,
            selected_task_notes=task_notes,
            active_skills=[],
            tool_signatures=list(task_contract.allowed_tools),
            retrieval_packets=retrieval_packets,
        )

    def prune_stale_items(
        self,
        task_contract: TaskContract,
        state_snapshot: StateSnapshot,
        *,
        recent_tool_results: list[object],
    ) -> list[str]:
        query_terms = self._query_terms(task_contract, state_snapshot.task_block)
        kept: list[str] = []

        for item in recent_tool_results:
            normalized = self._normalize_tool_result(item)
            if normalized is None:
                continue
            if normalized["is_stale"]:
                continue
            if normalized["related_task_id"] not in ("", state_snapshot.task_block.task_id):
                continue
            if not self._is_relevant(normalized["text"], query_terms):
                continue

            tool_name = normalized["tool"] or "tool"
            kept.append(f"{tool_name}: {normalized['text']}")
            if len(kept) >= self.MAX_TOOL_RESULTS:
                break

        return kept

    def serialize_working_context(self, working_context: WorkingContext) -> dict[str, object]:
        return self._to_json_value(working_context)

    def _build_task_notes(
        self,
        task_block: TaskBlock,
        *,
        distilled_summary: str | None,
    ) -> list[str]:
        notes: list[str] = [f"Task goal: {task_block.current_goal}"]
        if distilled_summary and distilled_summary.strip():
            notes.append(f"Distilled summary: {distilled_summary.strip()}")

        for blocker in task_block.blockers:
            notes.append(f"Blocker: {blocker}")
        for next_step in task_block.next_steps:
            notes.append(f"Next step: {next_step}")
        for risk in task_block.known_risks:
            notes.append(f"Known risk: {risk}")
        for assumption in task_block.assumptions:
            notes.append(f"Assumption: {assumption}")

        return notes[: self.MAX_TASK_NOTES]

    def _build_project_notes(
        self,
        task_contract: TaskContract,
        state_snapshot: StateSnapshot,
    ) -> list[str]:
        query_terms = self._query_terms(task_contract, state_snapshot.task_block)
        candidates: list[tuple[str, bool]] = []

        if state_snapshot.project_block.current_phase:
            candidates.append(
                (f"Project phase: {state_snapshot.project_block.current_phase}", True)
            )
        candidates.extend(
            (f"Project goal: {goal}", False)
            for goal in state_snapshot.project_block.goals
        )
        candidates.extend(
            (f"Project context: {fact}", False)
            for fact in state_snapshot.project_block.background_facts
        )
        candidates.extend(
            (f"Key dependency: {dependency}", False)
            for dependency in state_snapshot.project_block.key_dependencies
        )
        candidates.extend(
            (f"Milestone: {milestone}", False)
            for milestone in state_snapshot.project_block.milestones
        )

        return self._select_notes(
            candidates,
            query_terms=query_terms,
            limit=self.MAX_PROJECT_NOTES,
        )

    def _build_global_notes(
        self,
        task_contract: TaskContract,
        state_snapshot: StateSnapshot,
    ) -> list[str]:
        query_terms = self._query_terms(task_contract, state_snapshot.task_block)
        candidates: list[tuple[str, bool]] = []
        candidates.extend(
            (f"Constraint: {constraint}", True)
            for constraint in state_snapshot.global_state.hard_constraints
        )
        candidates.extend(
            (f"Principle: {principle}", False)
            for principle in state_snapshot.global_state.operating_principles
        )
        candidates.extend(
            (f"Default permission: {permission}", True)
            for permission in state_snapshot.global_state.permission_defaults
        )
        candidates.extend(
            (f"Preferred tool: {tool}", False)
            for tool in state_snapshot.global_state.preferred_tools
        )

        return self._select_notes(
            candidates,
            query_terms=query_terms,
            limit=self.MAX_GLOBAL_NOTES,
        )

    def _build_journal_packets(self, journal_lessons: list[object]) -> list[str]:
        packets: list[str] = []
        for lesson in journal_lessons:
            normalized = self._normalize_journal_lesson(lesson)
            if normalized is None:
                continue
            if normalized in packets:
                continue
            packets.append(normalized)
            if len(packets) >= self.MAX_JOURNAL_LESSONS:
                break
        return packets

    def _select_notes(
        self,
        candidates: list[tuple[str, bool]],
        *,
        query_terms: set[str],
        limit: int,
    ) -> list[str]:
        always_include: list[str] = []
        relevant: list[tuple[int, str]] = []
        seen: set[str] = set()

        for note, include_without_overlap in candidates:
            normalized_note = note.strip()
            if not normalized_note or normalized_note in seen:
                continue
            seen.add(normalized_note)

            score = self._relevance_score(normalized_note, query_terms)
            if score > 0:
                relevant.append((score, normalized_note))
            elif include_without_overlap:
                always_include.append(normalized_note)

        relevant.sort(key=lambda item: (-item[0], item[1]))
        ordered = always_include + [note for _, note in relevant]
        return ordered[:limit]

    def _query_terms(
        self,
        task_contract: TaskContract,
        task_block: TaskBlock,
    ) -> set[str]:
        terms = set(self._tokenize(task_contract.goal))
        terms.update(self._tokenize(task_block.current_goal))
        for item in task_contract.success_criteria:
            terms.update(self._tokenize(item))
        return terms

    def _relevance_score(self, text: str, query_terms: set[str]) -> int:
        text_terms = set(self._tokenize(text))
        return len(text_terms & query_terms)

    def _is_relevant(self, text: str, query_terms: set[str]) -> bool:
        return self._relevance_score(text, query_terms) > 0

    def _normalize_tool_result(self, item: object) -> dict[str, str | bool] | None:
        if isinstance(item, str):
            text = item.strip()
            if not text:
                return None
            return {
                "tool": "",
                "text": text,
                "related_task_id": "",
                "is_stale": False,
            }

        if not isinstance(item, dict):
            return None

        text = str(
            item.get("summary")
            or item.get("content")
            or item.get("result")
            or ""
        ).strip()
        if not text:
            return None

        status = str(item.get("status") or "").strip().lower()
        is_stale = bool(item.get("is_stale")) or status in {"stale", "obsolete"}
        return {
            "tool": str(item.get("tool") or "").strip(),
            "text": text,
            "related_task_id": str(item.get("related_task_id") or "").strip(),
            "is_stale": is_stale,
        }

    def _normalize_journal_lesson(self, item: object) -> str | None:
        if isinstance(item, str):
            text = item.strip()
            return f"Learning lesson: {text}" if text else None

        if not isinstance(item, dict):
            return None

        lesson = str(item.get("lesson") or "").strip()
        if not lesson:
            return None
        source = str(item.get("source") or "lesson").strip().lower()
        return f"Learning lesson ({source}): {lesson}"

    def _tokenize(self, text: str) -> list[str]:
        stop_words = {
            "a",
            "an",
            "and",
            "are",
            "for",
            "from",
            "into",
            "is",
            "of",
            "on",
            "or",
            "that",
            "the",
            "this",
            "to",
            "with",
        }
        return [
            token
            for token in re.findall(r"[A-Za-z0-9_]+", text.lower())
            if len(token) > 1 and token not in stop_words
        ]

    def _to_json_value(self, value: object) -> object:
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return {
                field.name: self._to_json_value(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, dict):
            return {
                str(key): self._to_json_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self._to_json_value(item) for item in value]
        return value
