from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any
import re

from harness.state.models import TaskContract, TaskBlock, WorkingContext
from harness.state.state_manager import StateSnapshot


class ContextEngine:
    """Assemble the smallest useful working context from structured state.

    v0.4 keeps selection explicit and small:
    - task state is primary
    - distilled summary is a compressed supplement, not a replacement for state
    - residual state is included only when it changes the current decision surface
    - journal lessons are active-only supplements and never a dominant context source
    - archived lessons and raw chat history stay out by default
    """

    BLOCK_PRIORITY = {
        "task_contract": 0,
        "task_block": 1,
        "distilled_summary": 2,
        "residual_state": 3,
        "project_block": 4,
        "global_state": 5,
        "journal_lessons_active": 6,
    }

    MAX_TASK_NOTES = 6
    MAX_TASK_BLOCK_NOTES = 5
    MAX_SUMMARY_NOTES = 1
    MAX_PROJECT_NOTES = 3
    MAX_GLOBAL_NOTES = 3
    MAX_TOOL_RESULTS = 3
    MAX_JOURNAL_LESSONS = 2
    MAX_RESIDUAL_PACKETS = 1

    def build_working_context(
        self,
        task_contract: TaskContract,
        state_snapshot: StateSnapshot,
        distilled_summary: str | None = None,
        recent_tool_results: list[object] | None = None,
        journal_lessons: list[object] | None = None,
    ) -> WorkingContext:
        selection = self.select_context_blocks(
            task_contract,
            state_snapshot,
            distilled_summary=distilled_summary,
            journal_lessons=journal_lessons,
        )
        pruned = self.prune_context_blocks(selection)
        tool_packets = self.prune_stale_items(
            task_contract,
            state_snapshot,
            recent_tool_results=recent_tool_results or [],
        )
        retrieval_packets = pruned["residual_packets"] + tool_packets + pruned["journal_packets"]

        return WorkingContext(
            task_contract=task_contract,
            selected_global_notes=pruned["global_notes"],
            selected_project_notes=pruned["project_notes"],
            selected_task_notes=pruned["task_notes"],
            active_skills=[],
            tool_signatures=list(task_contract.allowed_tools),
            retrieval_packets=retrieval_packets,
        )

    def select_context_blocks(
        self,
        task_contract: TaskContract,
        state_snapshot: StateSnapshot,
        *,
        distilled_summary: str | None = None,
        journal_lessons: list[object] | None = None,
    ) -> dict[str, Any]:
        task_block_notes = self._build_task_block_notes(state_snapshot.task_block)
        summary_notes = self._build_summary_notes(distilled_summary)
        residual_notes = self._build_residual_notes(state_snapshot.task_block)
        project_notes = self._build_project_notes(task_contract, state_snapshot)
        global_notes = self._build_global_notes(task_contract, state_snapshot)
        journal_packets, journal_meta = self._build_journal_packets(journal_lessons or [])

        blocks = {
            "task_contract": self._make_block(
                "task_contract",
                usage="boundary",
                content=task_contract,
                included=True,
                reason="contract_boundary_always_included",
                max_items=1,
            ),
            "task_block": self._make_block(
                "task_block",
                usage="primary_notes",
                content=task_block_notes,
                included=bool(task_block_notes),
                reason=(
                    "task_state_prioritized"
                    if task_block_notes
                    else "task_block_empty"
                ),
                max_items=self.MAX_TASK_BLOCK_NOTES,
            ),
            "distilled_summary": self._make_block(
                "distilled_summary",
                usage="supplement_note",
                content=summary_notes,
                included=bool(summary_notes),
                reason=(
                    "summary_as_compressed_supplement"
                    if summary_notes
                    else "no_distilled_summary"
                ),
                max_items=self.MAX_SUMMARY_NOTES,
            ),
            "residual_state": self._make_block(
                "residual_state",
                usage="supplement_packet",
                content=residual_notes,
                included=bool(residual_notes),
                reason=(
                    "residual_state_relevant_to_current_decision"
                    if residual_notes
                    else "residual_state_not_actionable"
                ),
                max_items=self.MAX_RESIDUAL_PACKETS,
            ),
            "project_block": self._make_block(
                "project_block",
                usage="supporting_notes",
                content=project_notes,
                included=bool(project_notes),
                reason=(
                    "project_context_relevant_after_task_state"
                    if project_notes
                    else "no_relevant_project_context"
                ),
                max_items=self.MAX_PROJECT_NOTES,
            ),
            "global_state": self._make_block(
                "global_state",
                usage="supporting_notes",
                content=global_notes,
                included=bool(global_notes),
                reason=(
                    "global_constraints_relevant_after_task_state"
                    if global_notes
                    else "no_relevant_global_state"
                ),
                max_items=self.MAX_GLOBAL_NOTES,
            ),
            "journal_lessons_active": self._make_block(
                "journal_lessons_active",
                usage="supplement_packet",
                content=journal_packets,
                included=bool(journal_packets),
                reason=self._journal_reason(journal_packets, journal_meta),
                max_items=self.MAX_JOURNAL_LESSONS,
            ),
        }
        return {
            "blocks": blocks,
            "selection_order": [
                name
                for name, _ in sorted(
                    self.BLOCK_PRIORITY.items(),
                    key=lambda item: item[1],
                )
            ],
        }

    def prune_context_blocks(self, selection: Mapping[str, Any]) -> dict[str, list[str]]:
        blocks = selection["blocks"]
        task_notes = list(blocks["task_block"]["content"][: self.MAX_TASK_BLOCK_NOTES])
        task_notes.extend(blocks["distilled_summary"]["content"][: self.MAX_SUMMARY_NOTES])
        task_notes = task_notes[: self.MAX_TASK_NOTES]

        return {
            "task_notes": task_notes,
            "project_notes": list(blocks["project_block"]["content"][: self.MAX_PROJECT_NOTES]),
            "global_notes": list(blocks["global_state"]["content"][: self.MAX_GLOBAL_NOTES]),
            "journal_packets": list(
                blocks["journal_lessons_active"]["content"][: self.MAX_JOURNAL_LESSONS]
            ),
            "residual_packets": list(blocks["residual_state"]["content"][: self.MAX_RESIDUAL_PACKETS]),
        }

    def build_block_selection_report(
        self,
        task_contract: TaskContract,
        state_snapshot: StateSnapshot,
        *,
        distilled_summary: str | None = None,
        journal_lessons: list[object] | None = None,
    ) -> dict[str, Any]:
        selection = self.select_context_blocks(
            task_contract,
            state_snapshot,
            distilled_summary=distilled_summary,
            journal_lessons=journal_lessons,
        )
        report = {
            "included_blocks": [],
            "excluded_blocks": [],
            "block_order": list(selection["selection_order"]),
            "limits": {
                "task_block": self.MAX_TASK_BLOCK_NOTES,
                "distilled_summary": self.MAX_SUMMARY_NOTES,
                "project_block": self.MAX_PROJECT_NOTES,
                "global_state": self.MAX_GLOBAL_NOTES,
                "journal_lessons_active": self.MAX_JOURNAL_LESSONS,
                "residual_state": self.MAX_RESIDUAL_PACKETS,
            },
        }

        for block_name in selection["selection_order"]:
            block = selection["blocks"][block_name]
            row = {
                "block": block_name,
                "priority": block["priority"],
                "usage": block["usage"],
                "reason": block["reason"],
                "item_count": block["item_count"],
            }
            if block["included"]:
                report["included_blocks"].append(row)
            else:
                report["excluded_blocks"].append(row)
        return report

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

    def _make_block(
        self,
        block_name: str,
        *,
        usage: str,
        content: object,
        included: bool,
        reason: str,
        max_items: int,
    ) -> dict[str, object]:
        if isinstance(content, list):
            item_count = len(content)
        elif content is None:
            item_count = 0
        else:
            item_count = 1
        return {
            "priority": self.BLOCK_PRIORITY[block_name],
            "usage": usage,
            "content": content,
            "included": included,
            "reason": reason,
            "max_items": max_items,
            "item_count": item_count,
        }

    def _build_task_block_notes(self, task_block: TaskBlock) -> list[str]:
        notes: list[str] = [f"Task goal: {task_block.current_goal}"]
        for blocker in task_block.blockers:
            notes.append(f"Blocker: {blocker}")
        for next_step in task_block.next_steps:
            notes.append(f"Next step: {next_step}")
        for risk in task_block.known_risks:
            notes.append(f"Known risk: {risk}")
        for assumption in task_block.assumptions:
            notes.append(f"Assumption: {assumption}")
        return notes[: self.MAX_TASK_BLOCK_NOTES]

    def _build_summary_notes(self, distilled_summary: str | None) -> list[str]:
        if not distilled_summary or not distilled_summary.strip():
            return []
        return [f"Distilled summary: {distilled_summary.strip()}"]

    def _build_residual_notes(self, task_block: TaskBlock) -> list[str]:
        if not self._should_include_residual_state(task_block):
            return []

        notes: list[str] = []
        residual = task_block.residual_risk or {}
        if isinstance(residual, dict):
            risk_level = str(
                residual.get("reassessed_level") or residual.get("previous_level") or ""
            ).strip().lower()
            if risk_level:
                notes.append(f"Residual state: risk {risk_level}")
        if task_block.followup_required:
            notes.append("Residual state: follow-up required")
        if task_block.governance_required:
            notes.append("Residual state: governance review required")
        return notes[: self.MAX_RESIDUAL_PACKETS]

    def _should_include_residual_state(self, task_block: TaskBlock) -> bool:
        if task_block.followup_required or task_block.governance_required:
            return True
        residual = task_block.residual_risk
        if not isinstance(residual, dict):
            return False
        risk_level = str(
            residual.get("reassessed_level") or residual.get("previous_level") or ""
        ).strip().lower()
        return risk_level in {"medium", "high"}

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

    def _build_journal_packets(self, journal_lessons: list[object]) -> tuple[list[str], dict[str, int]]:
        packets: list[str] = []
        seen: set[str] = set()
        archived_skipped = 0
        invalid_skipped = 0

        for lesson in journal_lessons:
            normalized = self._normalize_journal_lesson(lesson)
            if normalized is None:
                if isinstance(lesson, dict) and str(lesson.get("archive_status") or "").strip().lower() == "archived":
                    archived_skipped += 1
                else:
                    invalid_skipped += 1
                continue
            if normalized in seen:
                continue
            packets.append(normalized)
            seen.add(normalized)
            if len(packets) >= self.MAX_JOURNAL_LESSONS:
                break

        return packets, {
            "archived_skipped": archived_skipped,
            "invalid_skipped": invalid_skipped,
        }

    def _journal_reason(self, journal_packets: list[str], journal_meta: dict[str, int]) -> str:
        if journal_packets and journal_meta["archived_skipped"] > 0:
            return "active_lessons_selected_archived_excluded"
        if journal_packets:
            return "active_lessons_selected_as_supplement"
        if journal_meta["archived_skipped"] > 0:
            return "archived_lessons_excluded_by_default"
        return "no_active_journal_lessons"

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

        archive_status = str(item.get("archive_status") or "active").strip().lower()
        if archive_status == "archived":
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
