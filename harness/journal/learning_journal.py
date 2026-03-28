from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
import json


class LearningJournal:
    """Persist small cross-task lessons without turning state into a history dump.

    Boundary notes:
    - task_block tracks the current task runtime state for this task only.
    - distilled_summary compresses the current task's progress so far.
    - failure journal may exist later for failure-event chains, but it is not implemented here.
    - learning_journal stores reusable lessons learned across tasks, so entries must stay concise
      and portable instead of copying full task state or raw execution history.
    """

    DEFAULT_LIMIT = 2
    VALID_SOURCES = {
        "success",
        "failure",
        "verification",
        "followup",
        "sandbox",
        "rollback",
    }

    def __init__(self, store_path: str | Path) -> None:
        self._store_path = Path(store_path)
        self.initialize_store()

    @property
    def store_path(self) -> Path:
        return self._store_path

    def initialize_store(self) -> Path:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._store_path.exists():
            self._store_path.write_text("", encoding="utf-8")
        return self._store_path

    def append_lesson(self, entry: Mapping[str, object]) -> dict[str, object]:
        normalized = self._normalize_entry(dict(entry))
        with self._store_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(normalized, ensure_ascii=True) + "\n")
        return normalized

    def read_relevant_lessons(
        self,
        task_type: str | None = None,
        tags: Sequence[str] | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict[str, object]]:
        if limit <= 0:
            return []

        requested_task_type = str(task_type or "").strip().lower()
        requested_tags = {
            str(tag).strip().lower()
            for tag in (tags or [])
            if str(tag).strip()
        }
        matches: list[dict[str, object]] = []

        for entry in self._iter_entries():
            if requested_task_type and str(entry["task_type"]).lower() != requested_task_type:
                continue

            entry_tags = {
                str(tag).strip().lower()
                for tag in entry.get("tags", [])
                if str(tag).strip()
            }
            if requested_tags and entry_tags.isdisjoint(requested_tags):
                continue
            matches.append(entry)

        matches.sort(key=lambda item: str(item["created_at"]), reverse=True)
        return matches[:limit]

    def build_lesson_entry(
        self,
        *,
        task_id: str,
        task_type: str,
        execution_result: Mapping[str, object] | None = None,
        verification_report: Mapping[str, object] | None = None,
        residual_snapshot: Mapping[str, object] | None = None,
        sandbox_result: Mapping[str, object] | None = None,
        rollback_result: Mapping[str, object] | None = None,
        lesson: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> dict[str, object]:
        normalized_task_id = str(task_id).strip()
        normalized_task_type = str(task_type).strip().lower()
        if not normalized_task_id:
            raise ValueError("task_id must not be empty")
        if not normalized_task_type:
            raise ValueError("task_type must not be empty")

        source = self._resolve_source(
            execution_result=execution_result,
            verification_report=verification_report,
            residual_snapshot=residual_snapshot,
            sandbox_result=sandbox_result,
            rollback_result=rollback_result,
        )
        tag_list = self._build_tags(
            task_type=normalized_task_type,
            source=source,
            execution_result=execution_result,
            residual_snapshot=residual_snapshot,
            sandbox_result=sandbox_result,
            rollback_result=rollback_result,
            tags=tags,
        )
        lesson_text = lesson.strip() if lesson and lesson.strip() else self._build_lesson_text(
            task_type=normalized_task_type,
            source=source,
            execution_result=execution_result,
            verification_report=verification_report,
            residual_snapshot=residual_snapshot,
            sandbox_result=sandbox_result,
            rollback_result=rollback_result,
        )

        return self._normalize_entry(
            {
                "entry_id": f"lesson-{uuid4().hex}",
                "task_id": normalized_task_id,
                "task_type": normalized_task_type,
                "tags": tag_list,
                "lesson": lesson_text,
                "source": source,
                "confidence": self._resolve_confidence(source, verification_report),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def _iter_entries(self) -> list[dict[str, object]]:
        if not self._store_path.exists():
            return []

        entries: list[dict[str, object]] = []
        for line_number, raw_line in enumerate(
            self._store_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"learning journal store contains invalid JSON on line {line_number}"
                ) from exc
            if not isinstance(payload, dict):
                raise ValueError(
                    f"learning journal store line {line_number} must contain a JSON object"
                )
            entries.append(self._normalize_entry(payload))
        return entries

    def _normalize_entry(self, entry: dict[str, object]) -> dict[str, object]:
        required_fields = {
            "entry_id",
            "task_id",
            "task_type",
            "tags",
            "lesson",
            "source",
            "confidence",
            "created_at",
        }
        missing = sorted(required_fields - set(entry))
        if missing:
            missing_fields = ", ".join(missing)
            raise ValueError(f"lesson entry missing required field(s): {missing_fields}")

        normalized = {
            "entry_id": str(entry["entry_id"]).strip(),
            "task_id": str(entry["task_id"]).strip(),
            "task_type": str(entry["task_type"]).strip().lower(),
            "tags": self._normalize_tags(entry["tags"]),
            "lesson": str(entry["lesson"]).strip(),
            "source": str(entry["source"]).strip().lower(),
            "confidence": self._normalize_confidence(entry["confidence"]),
            "created_at": str(entry["created_at"]).strip(),
        }

        if not normalized["entry_id"]:
            raise ValueError("entry_id must not be empty")
        if not normalized["task_id"]:
            raise ValueError("task_id must not be empty")
        if not normalized["task_type"]:
            raise ValueError("task_type must not be empty")
        if not normalized["lesson"]:
            raise ValueError("lesson must not be empty")
        if normalized["source"] not in self.VALID_SOURCES:
            raise ValueError(
                "source must be one of success, failure, verification, followup, sandbox, or rollback"
            )
        if not normalized["created_at"]:
            raise ValueError("created_at must not be empty")
        return normalized

    def _normalize_tags(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            candidate_tags = [value]
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            candidate_tags = list(value)
        else:
            raise TypeError("tags must be a string or sequence of strings")

        normalized: list[str] = []
        seen: set[str] = set()
        for candidate in candidate_tags:
            tag = str(candidate).strip().lower()
            if not tag or tag in seen:
                continue
            normalized.append(tag)
            seen.add(tag)
        return normalized

    def _normalize_confidence(self, value: object) -> float:
        try:
            normalized = float(value)
        except (TypeError, ValueError) as exc:
            raise TypeError("confidence must be numeric") from exc
        if normalized < 0 or normalized > 1:
            raise ValueError("confidence must be between 0 and 1")
        return round(normalized, 2)

    def _resolve_source(
        self,
        *,
        execution_result: Mapping[str, object] | None,
        verification_report: Mapping[str, object] | None,
        residual_snapshot: Mapping[str, object] | None,
        sandbox_result: Mapping[str, object] | None,
        rollback_result: Mapping[str, object] | None,
    ) -> str:
        rollback_status = str(rollback_result.get("status") or "").strip().lower() if rollback_result else ""
        sandbox_status = str(sandbox_result.get("status") or "").strip().lower() if sandbox_result else ""
        execution_status = str(execution_result.get("status") or "").strip().lower() if execution_result else ""

        if rollback_status == "rolled_back":
            return "rollback"
        if sandbox_status == "error":
            return "sandbox"
        if execution_status == "error":
            return "failure"
        if residual_snapshot:
            if bool(residual_snapshot.get("followup_required")) or bool(
                residual_snapshot.get("governance_required")
            ):
                return "followup"
        if sandbox_status == "success":
            return "sandbox"
        if verification_report and not bool(verification_report.get("passed", False)):
            return "verification"
        return "success"

    def _build_tags(
        self,
        *,
        task_type: str,
        source: str,
        execution_result: Mapping[str, object] | None,
        residual_snapshot: Mapping[str, object] | None,
        sandbox_result: Mapping[str, object] | None,
        rollback_result: Mapping[str, object] | None,
        tags: Sequence[str] | None,
    ) -> list[str]:
        tag_list: list[str] = [task_type, source]
        if execution_result:
            tool_name = str(execution_result.get("tool_name") or "").strip().lower()
            if tool_name:
                tag_list.append(f"tool:{tool_name}")
            error_payload = execution_result.get("error")
            if isinstance(error_payload, Mapping):
                error_type = str(error_payload.get("type") or "").strip().lower()
                if error_type:
                    tag_list.append(f"error:{error_type}")
        if residual_snapshot:
            residual_risk = residual_snapshot.get("residual_risk")
            if isinstance(residual_risk, Mapping):
                risk_level = str(
                    residual_risk.get("reassessed_level") or residual_risk.get("previous_level") or ""
                ).strip().lower()
                if risk_level:
                    tag_list.append(f"risk:{risk_level}")
            if bool(residual_snapshot.get("followup_required")):
                tag_list.append("followup_required")
            if bool(residual_snapshot.get("governance_required")):
                tag_list.append("governance_required")
        if sandbox_result:
            tag_list.append("sandbox_required")
            sandbox_status = str(sandbox_result.get("status") or "").strip().lower()
            if sandbox_status == "success":
                tag_list.append("sandbox_success")
            elif sandbox_status == "error":
                tag_list.append("sandbox_failed")
        if rollback_result:
            rollback_status = str(rollback_result.get("status") or "").strip().lower()
            if rollback_status == "rolled_back":
                tag_list.append("rollback_triggered")
            elif rollback_status == "error":
                tag_list.append("rollback_failed")
        if tags:
            tag_list.extend(str(tag) for tag in tags)
        return self._normalize_tags(tag_list)

    def _build_lesson_text(
        self,
        *,
        task_type: str,
        source: str,
        execution_result: Mapping[str, object] | None,
        verification_report: Mapping[str, object] | None,
        residual_snapshot: Mapping[str, object] | None,
        sandbox_result: Mapping[str, object] | None,
        rollback_result: Mapping[str, object] | None,
    ) -> str:
        if source == "rollback":
            return (
                f"For {task_type} tasks, if isolated execution fails and rollback is triggered, "
                "inspect the gated write path before retrying or widening scope."
            )

        if source == "sandbox":
            sandbox_status = str(sandbox_result.get("status") or "").strip().lower() if sandbox_result else ""
            if sandbox_status == "error":
                return (
                    f"For {task_type} tasks, when sandboxed execution fails, narrow the risky action "
                    "instead of retrying the same isolated path immediately."
                )
            return (
                f"For {task_type} tasks, keep high-risk or write-capable steps isolated and validate "
                "the sandboxed outcome before promoting further changes."
            )

        if source == "followup":
            residual_risk = residual_snapshot.get("residual_risk") if residual_snapshot else None
            risk_level = "elevated"
            if isinstance(residual_risk, Mapping):
                risk_level = str(
                    residual_risk.get("reassessed_level") or residual_risk.get("previous_level") or risk_level
                ).strip().lower() or risk_level
            return (
                f"For {task_type} tasks, keep follow-up explicit when residual risk stays {risk_level} "
                "instead of broadening scope in the same pass."
            )

        if source == "failure":
            error_type = "execution_error"
            if execution_result and isinstance(execution_result.get("error"), Mapping):
                error_type = str(execution_result["error"].get("type") or error_type).strip().lower()
            return (
                f"For {task_type} tasks, when {error_type} appears, stop and adjust inputs or method "
                "before retrying the same path."
            )

        if source == "verification":
            issue_count = 0
            if verification_report:
                issue_count = len(list(verification_report.get("issues", [])))
            return (
                f"For {task_type} tasks, treat unresolved verification issues as incomplete work "
                f"and close the {issue_count} open issue(s) before calling the result done."
            )

        tool_name = "the allowed tool set"
        if execution_result:
            maybe_tool = str(execution_result.get("tool_name") or "").strip()
            if maybe_tool:
                tool_name = maybe_tool
        return (
            f"For {task_type} tasks, keep the scope tied to the success criteria and verify the output "
            f"after using {tool_name}."
        )

    def _resolve_confidence(
        self,
        source: str,
        verification_report: Mapping[str, object] | None,
    ) -> float:
        if source == "rollback":
            return 0.9
        if source == "sandbox":
            return 0.85
        if source == "followup":
            return 0.85
        if source == "failure":
            return 0.8
        if source == "verification":
            issue_count = len(list(verification_report.get("issues", []))) if verification_report else 0
            return 0.8 if issue_count > 0 else 0.7
        return 0.65
