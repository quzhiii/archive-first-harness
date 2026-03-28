from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Generic, TypeVar
import json
import re

from harness.state.models import GlobalState, ProjectBlock, TaskBlock


T = TypeVar("T")


class StateVersionConflictError(RuntimeError):
    """Raised when a caller tries to write a stale state version."""


@dataclass(slots=True)
class VersionedState(Generic[T]):
    value: T
    version: int


@dataclass(slots=True)
class StateSnapshot:
    global_state: GlobalState
    project_block: ProjectBlock
    task_block: TaskBlock
    versions: dict[str, int]
    chat_history: list[str] | None = None


class StateManager:
    """File-backed state store with conservative merge semantics."""

    def __init__(self, storage_dir: str | Path) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def load_global_state(self) -> VersionedState[GlobalState]:
        return self._load_record(
            self._global_state_path(),
            lambda: GlobalState(),
            self._payload_to_global_state,
        )

    def load_project_block(self) -> VersionedState[ProjectBlock]:
        return self._load_record(
            self._project_block_path(),
            self._default_project_block,
            self._payload_to_project_block,
        )

    def load_task_block(self, task_id: str) -> VersionedState[TaskBlock]:
        normalized_task_id = task_id.strip()
        if not normalized_task_id:
            raise ValueError("task_id must not be empty")

        return self._load_record(
            self._task_block_path(normalized_task_id),
            lambda: self._default_task_block(normalized_task_id),
            self._payload_to_task_block,
        )

    def save_global_state(
        self,
        state: GlobalState,
        *,
        expected_version: int | None = None,
    ) -> VersionedState[GlobalState]:
        return self._write_record(
            self._global_state_path(),
            state,
            expected_version=expected_version,
        )

    def save_project_block(
        self,
        project_block: ProjectBlock,
        *,
        expected_version: int | None = None,
    ) -> VersionedState[ProjectBlock]:
        return self._write_record(
            self._project_block_path(),
            project_block,
            expected_version=expected_version,
        )

    def save_task_block(
        self,
        task_block: TaskBlock,
        *,
        expected_version: int | None = None,
    ) -> VersionedState[TaskBlock]:
        return self._write_record(
            self._task_block_path(task_block.task_id),
            task_block,
            expected_version=expected_version,
        )

    def update_task_block(
        self,
        task_id: str,
        updates: dict[str, object],
        *,
        expected_version: int,
        replace_fields: set[str] | None = None,
    ) -> VersionedState[TaskBlock]:
        current = self.load_task_block(task_id)
        if current.version != expected_version:
            raise StateVersionConflictError(
                f"task_block version conflict for '{task_id}': "
                f"expected {expected_version}, current {current.version}"
            )

        merged = self._merge_task_block(
            current.value,
            updates,
            replace_fields=replace_fields or set(),
        )
        return self.save_task_block(merged, expected_version=current.version)

    def apply_residual_writeback(
        self,
        writeback_payload: dict[str, object],
        *,
        expected_version: int,
    ) -> VersionedState[TaskBlock]:
        if not isinstance(writeback_payload, dict):
            raise TypeError("writeback_payload must be a dictionary")

        task_id = self._string_value(writeback_payload.get("task_id"))
        if not task_id:
            raise ValueError("writeback_payload must include a task_id")

        required_fields = {"residual_risk", "followup_required", "governance_required"}
        missing_fields = [
            field_name for field_name in sorted(required_fields) if field_name not in writeback_payload
        ]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(f"writeback_payload missing required field(s): {missing}")

        return self.update_task_block(
            task_id,
            {
                "residual_risk": writeback_payload["residual_risk"],
                "followup_required": writeback_payload["followup_required"],
                "governance_required": writeback_payload["governance_required"],
            },
            expected_version=expected_version,
            replace_fields=required_fields,
        )

    def build_state_snapshot_for_context(self, task_id: str) -> StateSnapshot:
        global_state = self.load_global_state()
        project_block = self.load_project_block()
        task_block = self.load_task_block(task_id)
        return StateSnapshot(
            global_state=global_state.value,
            project_block=project_block.value,
            task_block=task_block.value,
            versions={
                "global_state": global_state.version,
                "project_block": project_block.version,
                "task_block": task_block.version,
            },
            chat_history=[],
        )

    def _merge_task_block(
        self,
        current: TaskBlock,
        updates: dict[str, object],
        *,
        replace_fields: set[str],
    ) -> TaskBlock:
        field_names = {field.name for field in fields(TaskBlock)}
        unknown_fields = set(updates) - field_names
        if unknown_fields:
            unknown = ", ".join(sorted(unknown_fields))
            raise ValueError(f"unknown task block field(s): {unknown}")

        merged: dict[str, object] = {
            "task_id": current.task_id,
            "current_goal": current.current_goal,
            "contract_id": current.contract_id,
            "assumptions": list(current.assumptions),
            "blockers": list(current.blockers),
            "next_steps": list(current.next_steps),
            "known_risks": list(current.known_risks),
            "residual_risk": dict(current.residual_risk) if current.residual_risk is not None else None,
            "followup_required": current.followup_required,
            "governance_required": current.governance_required,
        }

        for field_name, value in updates.items():
            if field_name == "task_id":
                normalized_task_id = str(value).strip()
                if normalized_task_id != current.task_id:
                    raise ValueError("task_id cannot be changed during update")
                continue

            if field_name in replace_fields:
                merged[field_name] = self._normalize_task_block_value(field_name, value)
                continue

            if self._is_empty_update(value):
                continue

            merged[field_name] = self._normalize_task_block_value(field_name, value)

        return TaskBlock(**merged)

    def _write_record(
        self,
        path: Path,
        model: T,
        *,
        expected_version: int | None,
    ) -> VersionedState[T]:
        current_version = 0
        if path.exists():
            existing = self._read_storage_file(path)
            current_version = int(existing["version"])

        if current_version > 0 and expected_version is None:
            raise StateVersionConflictError(
                f"refusing to overwrite existing state at '{path.name}' without "
                "an expected_version"
            )
        if expected_version is not None and current_version != expected_version:
            raise StateVersionConflictError(
                f"version conflict for '{path.name}': expected {expected_version}, "
                f"current {current_version}"
            )

        next_version = current_version + 1
        payload = {
            "version": next_version,
            "updated_at": datetime.now(UTC).isoformat(),
            "data": self._to_json_value(model),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return VersionedState(value=model, version=next_version)

    def _load_record(
        self,
        path: Path,
        default_factory,
        parser,
    ) -> VersionedState[T]:
        if not path.exists():
            return VersionedState(value=default_factory(), version=0)

        payload = self._read_storage_file(path)
        return VersionedState(
            value=parser(payload["data"]),
            version=int(payload["version"]),
        )

    def _read_storage_file(self, path: Path) -> dict[str, object]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"state file '{path.name}' contains invalid JSON") from exc

        if not isinstance(data, dict):
            raise ValueError(f"state file '{path.name}' must contain a JSON object")
        if "version" not in data or "data" not in data:
            raise ValueError(
                f"state file '{path.name}' must contain 'version' and 'data' fields"
            )
        return data

    def _global_state_path(self) -> Path:
        return self._storage_dir / "global_state.json"

    def _project_block_path(self) -> Path:
        return self._storage_dir / "project_block.json"

    def _task_block_path(self, task_id: str) -> Path:
        safe_task_id = re.sub(r"[^A-Za-z0-9._-]+", "_", task_id.strip())
        return self._storage_dir / f"task_block_{safe_task_id}.json"

    def _default_project_block(self) -> ProjectBlock:
        return ProjectBlock(project_id="default", project_name="default")

    def _default_task_block(self, task_id: str) -> TaskBlock:
        return TaskBlock(task_id=task_id, current_goal="No active goal recorded.")

    def _payload_to_global_state(self, payload: dict[str, object]) -> GlobalState:
        return GlobalState(
            operating_principles=self._string_list(payload.get("operating_principles")),
            hard_constraints=self._string_list(payload.get("hard_constraints")),
            permission_defaults=self._string_list(payload.get("permission_defaults")),
            preferred_tools=self._string_list(payload.get("preferred_tools")),
        )

    def _payload_to_project_block(self, payload: dict[str, object]) -> ProjectBlock:
        return ProjectBlock(
            project_id=self._string_value(payload.get("project_id"), "default"),
            project_name=self._string_value(payload.get("project_name"), "default"),
            current_phase=self._string_value(payload.get("current_phase"), ""),
            goals=self._string_list(payload.get("goals")),
            key_dependencies=self._string_list(payload.get("key_dependencies")),
            milestones=self._string_list(payload.get("milestones")),
            background_facts=self._string_list(payload.get("background_facts")),
        )

    def _payload_to_task_block(self, payload: dict[str, object]) -> TaskBlock:
        return TaskBlock(
            task_id=self._string_value(payload.get("task_id"), "default-task"),
            current_goal=self._string_value(
                payload.get("current_goal"), "No active goal recorded."
            ),
            contract_id=self._optional_string_value(payload.get("contract_id")),
            assumptions=self._string_list(payload.get("assumptions")),
            blockers=self._string_list(payload.get("blockers")),
            next_steps=self._string_list(payload.get("next_steps")),
            known_risks=self._string_list(payload.get("known_risks")),
            residual_risk=self._dict_value(payload.get("residual_risk")),
            followup_required=self._bool_value(payload.get("followup_required"), False),
            governance_required=self._bool_value(payload.get("governance_required"), False),
        )

    def _normalize_task_block_value(self, field_name: str, value: object) -> object:
        list_fields = {"assumptions", "blockers", "next_steps", "known_risks"}
        bool_fields = {"followup_required", "governance_required"}
        if field_name in list_fields:
            return self._string_list(value)
        if field_name == "contract_id":
            return self._optional_string_value(value)
        if field_name == "residual_risk":
            return self._dict_value(value)
        if field_name in bool_fields:
            return self._bool_value(value, False)
        return self._string_value(value)

    def _string_list(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            item = value.strip()
            return [item] if item else []
        if isinstance(value, list):
            items: list[str] = []
            for item in value:
                text = str(item).strip()
                if text:
                    items.append(text)
            return items
        raise TypeError("expected a string or list of strings")

    def _string_value(self, value: object, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    def _optional_string_value(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _dict_value(self, value: object) -> dict[str, object] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise TypeError("expected a dictionary")
        return dict(value)

    def _bool_value(self, value: object, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        raise TypeError("expected a boolean")

    def _is_empty_update(self, value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, list):
            return len(self._string_list(value)) == 0
        return False

    def _to_json_value(self, value: object) -> object:
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return {
                field.name: self._to_json_value(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, dict):
            {
                str(key): self._to_json_value(item)
                for key, item in value.items()
            }
            return {
                str(key): self._to_json_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self._to_json_value(item) for item in value]
        return value
