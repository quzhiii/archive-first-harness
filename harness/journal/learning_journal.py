from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
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

    v0.4 quality control stays intentionally lightweight:
    - entries are either `active` or `archived`
    - dedup is fingerprint-based, not semantic
    - expired or low-signal entries are archived instead of deleted
    - archived entries are preserved but excluded from normal reads
    """

    DEFAULT_LIMIT = 2
    DEFAULT_TTL_DAYS = 30
    MIN_ACTIVE_CONFIDENCE = 0.5
    VALID_SOURCES = {
        "success",
        "failure",
        "verification",
        "followup",
        "sandbox",
        "rollback",
    }
    VALID_ARCHIVE_STATUSES = {"active", "archived"}
    MANUAL_ARCHIVE_REASON = "manual"

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
        now = self._utc_now()
        entries = self._iter_entries()
        entries, _ = self._apply_quality_controls(entries, now=now)
        candidate = self._normalize_entry(dict(entry), now=now)

        duplicate_index = self._find_duplicate_index(entries, candidate)
        if duplicate_index is not None:
            entries[duplicate_index] = self._merge_duplicate(
                existing=entries[duplicate_index],
                candidate=candidate,
                now=now,
            )
        else:
            entries.append(candidate)

        entries, _ = self._apply_quality_controls(entries, now=now)
        self._write_entries(entries)

        persisted = self._find_entry(entries, candidate["entry_id"])
        if persisted is not None:
            return persisted

        duplicate = self._find_duplicate_entry(entries, candidate)
        if duplicate is not None:
            return duplicate
        raise RuntimeError("learning journal failed to persist the lesson entry")

    def read_relevant_lessons(
        self,
        task_type: str | None = None,
        tags: Sequence[str] | None = None,
        limit: int = DEFAULT_LIMIT,
        include_archived: bool = False,
    ) -> list[dict[str, object]]:
        if limit <= 0:
            return []

        requested_task_type = str(task_type or "").strip().lower()
        requested_tags = {
            str(tag).strip().lower()
            for tag in (tags or [])
            if str(tag).strip()
        }
        now = self._utc_now()
        entries = self._iter_entries()
        entries, changed = self._apply_quality_controls(entries, now=now)

        matches: list[dict[str, object]] = []
        matched_ids: set[str] = set()
        for entry in entries:
            if not include_archived and entry["archive_status"] != "active":
                continue
            if requested_task_type and str(entry["task_type"]).lower() != requested_task_type:
                continue

            entry_tags = {
                str(tag).strip().lower()
                for tag in entry.get("tags", [])
                if str(tag).strip()
            }
            if requested_tags and entry_tags.isdisjoint(requested_tags):
                continue
            matches.append(dict(entry))
            matched_ids.add(str(entry["entry_id"]))

        matches.sort(key=self._sort_key, reverse=True)
        selected = matches[:limit]

        if selected:
            selected_ids = {str(entry["entry_id"]) for entry in selected}
            changed = self._touch_entries(entries, selected_ids, now=now) or changed
            for entry in selected:
                entry["last_accessed_at"] = now.isoformat()

        if changed:
            self._write_entries(entries)
        return selected

    def archive_entry(self, entry_id: str) -> dict[str, object]:
        normalized_entry_id = str(entry_id).strip()
        if not normalized_entry_id:
            raise ValueError("entry_id must not be empty")

        entries = self._iter_entries()
        for entry in entries:
            if entry["entry_id"] != normalized_entry_id:
                continue
            entry["archive_status"] = "archived"
            entry["archive_reason"] = self.MANUAL_ARCHIVE_REASON
            self._write_entries(entries)
            return dict(entry)

        raise ValueError(f"unknown lesson entry_id: {normalized_entry_id}")

    def should_archive(
        self,
        entry: Mapping[str, object],
        *,
        duplicate_exists: bool = False,
        now: datetime | None = None,
    ) -> dict[str, object]:
        normalized = self._normalize_entry(dict(entry), now=now)
        if normalized.get("archive_reason") == self.MANUAL_ARCHIVE_REASON:
            return {"archive": True, "reason": self.MANUAL_ARCHIVE_REASON}
        if duplicate_exists:
            return {"archive": True, "reason": "duplicate"}
        if self._is_expired(normalized, now=now):
            return {"archive": True, "reason": "expired"}
        if float(normalized["confidence"]) < self.MIN_ACTIVE_CONFIDENCE:
            return {"archive": True, "reason": "low_confidence"}
        return {"archive": False, "reason": None}

    def dedup_fingerprint(self, entry: Mapping[str, object]) -> str:
        normalized = self._normalize_entry(dict(entry))
        fingerprint_payload = {
            "task_type": normalized["task_type"],
            "source": normalized["source"],
            "lesson": normalized["lesson"],
            "tags": sorted(normalized["tags"]),
        }
        return json.dumps(
            fingerprint_payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    def apply_quality_controls(self) -> dict[str, int]:
        entries = self._iter_entries()
        entries, summary = self._apply_quality_controls(entries, now=self._utc_now())
        self._write_entries(entries)
        return summary

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

        # Keep the builder output backward compatible; quality-control fields are added at persist time.
        return {
            "entry_id": f"lesson-{uuid4().hex}",
            "task_id": normalized_task_id,
            "task_type": normalized_task_type,
            "tags": self._normalize_tags(tag_list),
            "lesson": lesson_text,
            "source": source,
            "confidence": self._resolve_confidence(source, verification_report),
            "created_at": datetime.now(UTC).isoformat(),
        }

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

    def _write_entries(self, entries: Sequence[Mapping[str, object]]) -> None:
        lines = [json.dumps(dict(entry), ensure_ascii=True) for entry in entries]
        payload = "\n".join(lines)
        if payload:
            payload += "\n"
        self._store_path.write_text(payload, encoding="utf-8")

    def _normalize_entry(
        self,
        entry: dict[str, object],
        *,
        now: datetime | None = None,
    ) -> dict[str, object]:
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
            "created_at": self._normalize_timestamp(entry["created_at"], field_name="created_at"),
            "archive_status": self._normalize_archive_status(entry.get("archive_status")),
            "ttl_days": self._normalize_ttl_days(entry.get("ttl_days")),
            "last_accessed_at": self._normalize_timestamp(
                entry.get("last_accessed_at") or entry["created_at"],
                field_name="last_accessed_at",
            ),
            "archive_reason": self._normalize_archive_reason(entry.get("archive_reason")),
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
        if normalized["archive_reason"] == self.MANUAL_ARCHIVE_REASON:
            normalized["archive_status"] = "archived"
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

    def _normalize_archive_status(self, value: object) -> str:
        normalized = str(value or "active").strip().lower()
        if normalized not in self.VALID_ARCHIVE_STATUSES:
            raise ValueError("archive_status must be 'active' or 'archived'")
        return normalized

    def _normalize_archive_reason(self, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        return normalized or None

    def _normalize_ttl_days(self, value: object) -> int:
        if value is None:
            return self.DEFAULT_TTL_DAYS
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise TypeError("ttl_days must be an integer") from exc
        if normalized < 0:
            raise ValueError("ttl_days must be zero or greater")
        return normalized

    def _normalize_timestamp(self, value: object, *, field_name: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be empty")
        self._parse_datetime(normalized, field_name=field_name)
        return normalized

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

    def _apply_quality_controls(
        self,
        entries: list[dict[str, object]],
        *,
        now: datetime,
    ) -> tuple[list[dict[str, object]], dict[str, int]]:
        updated = [dict(entry) for entry in entries]
        summary = {
            "active": 0,
            "archived": 0,
            "expired_archived": 0,
            "low_confidence_archived": 0,
            "deduplicated": 0,
        }

        for entry in updated:
            decision = self.should_archive(entry, now=now)
            if bool(decision["archive"]):
                entry["archive_status"] = "archived"
                entry["archive_reason"] = str(decision["reason"] or "archived")
                if entry["archive_reason"] == "expired":
                    summary["expired_archived"] += 1
                elif entry["archive_reason"] == "low_confidence":
                    summary["low_confidence_archived"] += 1
            else:
                entry["archive_status"] = "active"
                entry["archive_reason"] = None

        active_groups: dict[str, list[int]] = {}
        for index, entry in enumerate(updated):
            if entry["archive_status"] != "active":
                continue
            fingerprint = self.dedup_fingerprint(entry)
            active_groups.setdefault(fingerprint, []).append(index)

        for indices in active_groups.values():
            if len(indices) <= 1:
                continue
            canonical_index = max(indices, key=lambda idx: self._canonical_rank(updated[idx]))
            for index in indices:
                if index == canonical_index:
                    continue
                updated[index]["archive_status"] = "archived"
                updated[index]["archive_reason"] = "duplicate"
                summary["deduplicated"] += 1

        for entry in updated:
            if entry["archive_status"] == "active":
                summary["active"] += 1
            else:
                summary["archived"] += 1

        return updated, summary

    def _touch_entries(
        self,
        entries: list[dict[str, object]],
        entry_ids: set[str],
        *,
        now: datetime,
    ) -> bool:
        changed = False
        timestamp = now.isoformat()
        for entry in entries:
            if entry["entry_id"] not in entry_ids:
                continue
            if entry["last_accessed_at"] == timestamp:
                continue
            entry["last_accessed_at"] = timestamp
            changed = True
        return changed

    def _find_duplicate_index(
        self,
        entries: Sequence[dict[str, object]],
        candidate: Mapping[str, object],
    ) -> int | None:
        candidate_fingerprint = self.dedup_fingerprint(candidate)
        best_index: int | None = None
        best_rank: tuple[object, ...] | None = None

        for index, entry in enumerate(entries):
            if self.dedup_fingerprint(entry) != candidate_fingerprint:
                continue
            rank = self._canonical_rank(entry)
            if best_rank is None or rank > best_rank:
                best_index = index
                best_rank = rank
        return best_index

    def _find_duplicate_entry(
        self,
        entries: Sequence[dict[str, object]],
        candidate: Mapping[str, object],
    ) -> dict[str, object] | None:
        duplicate_index = self._find_duplicate_index(list(entries), candidate)
        if duplicate_index is None:
            return None
        return dict(entries[duplicate_index])

    def _merge_duplicate(
        self,
        *,
        existing: Mapping[str, object],
        candidate: Mapping[str, object],
        now: datetime,
    ) -> dict[str, object]:
        merged = dict(existing)
        merged.update(
            {
                "task_id": str(candidate["task_id"]),
                "task_type": str(candidate["task_type"]),
                "tags": list(candidate["tags"]),
                "lesson": str(candidate["lesson"]),
                "source": str(candidate["source"]),
                "confidence": max(float(existing["confidence"]), float(candidate["confidence"])),
                "created_at": str(candidate["created_at"]),
                "ttl_days": max(int(existing["ttl_days"]), int(candidate["ttl_days"])),
                "last_accessed_at": now.isoformat(),
            }
        )
        if str(existing.get("archive_reason") or "") != self.MANUAL_ARCHIVE_REASON:
            merged["archive_status"] = "active"
            merged["archive_reason"] = None
        return self._normalize_entry(merged, now=now)

    def _find_entry(
        self,
        entries: Sequence[dict[str, object]],
        entry_id: str,
    ) -> dict[str, object] | None:
        for entry in entries:
            if entry["entry_id"] == entry_id:
                return dict(entry)
        return None

    def _is_expired(
        self,
        entry: Mapping[str, object],
        *,
        now: datetime | None,
    ) -> bool:
        current_time = now or self._utc_now()
        created_at = self._parse_datetime(str(entry["created_at"]), field_name="created_at")
        ttl_days = int(entry.get("ttl_days", self.DEFAULT_TTL_DAYS))
        expiry_time = created_at + timedelta(days=ttl_days)
        return current_time >= expiry_time

    def _canonical_rank(self, entry: Mapping[str, object]) -> tuple[object, ...]:
        return (
            1 if entry.get("archive_status") == "active" else 0,
            float(entry["confidence"]),
            self._parse_datetime(str(entry["last_accessed_at"]), field_name="last_accessed_at"),
            self._parse_datetime(str(entry["created_at"]), field_name="created_at"),
            str(entry["entry_id"]),
        )

    def _sort_key(self, entry: Mapping[str, object]) -> tuple[datetime, datetime, str]:
        return (
            self._parse_datetime(str(entry["last_accessed_at"]), field_name="last_accessed_at"),
            self._parse_datetime(str(entry["created_at"]), field_name="created_at"),
            str(entry["entry_id"]),
        )

    def _parse_datetime(self, value: str, *, field_name: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _utc_now(self) -> datetime:
        return datetime.now(UTC)
