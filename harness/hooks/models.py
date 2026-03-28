from __future__ import annotations

"""Minimal hook payload contracts for the v0.3 event skeleton.

Anti-bloat rule:
- payloads keep only the fields required to route or inspect a single event
- payloads may carry short summaries or references
- payloads must not carry full state dumps, raw log bodies, environment echoes,
  or complete execution traces
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


HOOK_PAYLOAD_SCHEMA_VERSION = "v0.3"
FORBIDDEN_BULK_FIELD_NAMES = frozenset(
    {
        "state_dump",
        "raw_logs",
        "environment_dump",
        "execution_trace",
        "full_state",
        "full_logs",
    }
)

ON_SESSION_START = "on_session_start"
ON_EXECUTION_RESULT = "on_execution_result"
ON_VERIFICATION_REPORT = "on_verification_report"
ON_RESIDUAL_FOLLOWUP = "on_residual_followup"
ON_GOVERNANCE_CHECK = "on_governance_check"
ON_SANDBOX_REQUIRED = "on_sandbox_required"
ON_JOURNAL_APPEND = "on_journal_append"

HOOK_EVENT_NAMES = frozenset(
    {
        ON_SESSION_START,
        ON_EXECUTION_RESULT,
        ON_VERIFICATION_REPORT,
        ON_RESIDUAL_FOLLOWUP,
        ON_GOVERNANCE_CHECK,
        ON_SANDBOX_REQUIRED,
        ON_JOURNAL_APPEND,
    }
)


def _new_event_id() -> str:
    return f"evt-{uuid4().hex}"


def _new_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _clean_string(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _clean_optional_string(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank when provided")
    return normalized


def _validate_base_fields(
    *,
    event_id: str,
    timestamp: str,
    task_id: str,
    contract_id: str | None,
    schema_version: str,
    contract_id_optional: bool,
) -> tuple[str, str, str, str | None, str]:
    normalized_event_id = _clean_string(event_id, "event_id")
    normalized_timestamp = _clean_string(timestamp, "timestamp")
    normalized_task_id = _clean_string(task_id, "task_id")
    normalized_contract_id = _clean_optional_string(contract_id, "contract_id")
    if not contract_id_optional and normalized_contract_id is None:
        raise ValueError("contract_id must not be None for this payload")
    normalized_schema_version = _clean_string(schema_version, "schema_version")
    if normalized_schema_version != HOOK_PAYLOAD_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version must be '{HOOK_PAYLOAD_SCHEMA_VERSION}'"
        )
    return (
        normalized_event_id,
        normalized_timestamp,
        normalized_task_id,
        normalized_contract_id,
        normalized_schema_version,
    )


@dataclass(slots=True)
class SessionStartPayload:
    task_id: str
    contract_id: str
    task_type: str
    residual_risk_level: str
    event_id: str = field(default_factory=_new_event_id)
    timestamp: str = field(default_factory=_new_timestamp)
    schema_version: str = HOOK_PAYLOAD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        (
            self.event_id,
            self.timestamp,
            self.task_id,
            self.contract_id,
            self.schema_version,
        ) = _validate_base_fields(
            event_id=self.event_id,
            timestamp=self.timestamp,
            task_id=self.task_id,
            contract_id=self.contract_id,
            schema_version=self.schema_version,
            contract_id_optional=False,
        )
        self.task_type = _clean_string(self.task_type, "task_type")
        self.residual_risk_level = _clean_string(
            self.residual_risk_level,
            "residual_risk_level",
        )


@dataclass(slots=True)
class ExecutionResultPayload:
    task_id: str
    contract_id: str
    execution_result: dict[str, Any]
    candidate_tools: list[dict[str, Any]] = field(default_factory=list)
    event_id: str = field(default_factory=_new_event_id)
    timestamp: str = field(default_factory=_new_timestamp)
    schema_version: str = HOOK_PAYLOAD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        (
            self.event_id,
            self.timestamp,
            self.task_id,
            self.contract_id,
            self.schema_version,
        ) = _validate_base_fields(
            event_id=self.event_id,
            timestamp=self.timestamp,
            task_id=self.task_id,
            contract_id=self.contract_id,
            schema_version=self.schema_version,
            contract_id_optional=False,
        )
        if not isinstance(self.execution_result, dict):
            raise TypeError("execution_result must be a dictionary")
        if not isinstance(self.candidate_tools, list):
            raise TypeError("candidate_tools must be a list")


@dataclass(slots=True)
class VerificationReportPayload:
    task_id: str
    contract_id: str
    verification_report: dict[str, Any]
    residual_risk_hint: str
    event_id: str = field(default_factory=_new_event_id)
    timestamp: str = field(default_factory=_new_timestamp)
    schema_version: str = HOOK_PAYLOAD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        (
            self.event_id,
            self.timestamp,
            self.task_id,
            self.contract_id,
            self.schema_version,
        ) = _validate_base_fields(
            event_id=self.event_id,
            timestamp=self.timestamp,
            task_id=self.task_id,
            contract_id=self.contract_id,
            schema_version=self.schema_version,
            contract_id_optional=False,
        )
        if not isinstance(self.verification_report, dict):
            raise TypeError("verification_report must be a dictionary")
        self.residual_risk_hint = _clean_string(
            self.residual_risk_hint,
            "residual_risk_hint",
        )


@dataclass(slots=True)
class ResidualFollowupPayload:
    task_id: str
    contract_id: str
    residual_reassessment: dict[str, Any]
    methodology_advice: dict[str, Any] | None = None
    model_advice: dict[str, Any] | None = None
    event_id: str = field(default_factory=_new_event_id)
    timestamp: str = field(default_factory=_new_timestamp)
    schema_version: str = HOOK_PAYLOAD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        (
            self.event_id,
            self.timestamp,
            self.task_id,
            self.contract_id,
            self.schema_version,
        ) = _validate_base_fields(
            event_id=self.event_id,
            timestamp=self.timestamp,
            task_id=self.task_id,
            contract_id=self.contract_id,
            schema_version=self.schema_version,
            contract_id_optional=False,
        )
        if not isinstance(self.residual_reassessment, dict):
            raise TypeError("residual_reassessment must be a dictionary")
        if self.methodology_advice is not None and not isinstance(self.methodology_advice, dict):
            raise TypeError("methodology_advice must be a dictionary when provided")
        if self.model_advice is not None and not isinstance(self.model_advice, dict):
            raise TypeError("model_advice must be a dictionary when provided")


@dataclass(slots=True)
class GovernanceCheckPayload:
    task_id: str
    contract_id: str
    advice_summary: dict[str, Any]
    governance_required: bool
    event_id: str = field(default_factory=_new_event_id)
    timestamp: str = field(default_factory=_new_timestamp)
    schema_version: str = HOOK_PAYLOAD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        (
            self.event_id,
            self.timestamp,
            self.task_id,
            self.contract_id,
            self.schema_version,
        ) = _validate_base_fields(
            event_id=self.event_id,
            timestamp=self.timestamp,
            task_id=self.task_id,
            contract_id=self.contract_id,
            schema_version=self.schema_version,
            contract_id_optional=False,
        )
        if not isinstance(self.advice_summary, dict):
            raise TypeError("advice_summary must be a dictionary")
        if not isinstance(self.governance_required, bool):
            raise TypeError("governance_required must be a boolean")


@dataclass(slots=True)
class SandboxRequiredPayload:
    task_id: str
    action: str
    risk_level: str
    write_permission_level: str
    contract_id: str | None = None
    event_id: str = field(default_factory=_new_event_id)
    timestamp: str = field(default_factory=_new_timestamp)
    schema_version: str = HOOK_PAYLOAD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        (
            self.event_id,
            self.timestamp,
            self.task_id,
            self.contract_id,
            self.schema_version,
        ) = _validate_base_fields(
            event_id=self.event_id,
            timestamp=self.timestamp,
            task_id=self.task_id,
            contract_id=self.contract_id,
            schema_version=self.schema_version,
            contract_id_optional=True,
        )
        self.action = _clean_string(self.action, "action")
        self.risk_level = _clean_string(self.risk_level, "risk_level")
        self.write_permission_level = _clean_string(
            self.write_permission_level,
            "write_permission_level",
        )


@dataclass(slots=True)
class JournalAppendPayload:
    task_id: str
    lesson_entry: dict[str, Any]
    source: str
    contract_id: str | None = None
    event_id: str = field(default_factory=_new_event_id)
    timestamp: str = field(default_factory=_new_timestamp)
    schema_version: str = HOOK_PAYLOAD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        (
            self.event_id,
            self.timestamp,
            self.task_id,
            self.contract_id,
            self.schema_version,
        ) = _validate_base_fields(
            event_id=self.event_id,
            timestamp=self.timestamp,
            task_id=self.task_id,
            contract_id=self.contract_id,
            schema_version=self.schema_version,
            contract_id_optional=True,
        )
        if not isinstance(self.lesson_entry, dict):
            raise TypeError("lesson_entry must be a dictionary")
        self.source = _clean_string(self.source, "source")


EVENT_PAYLOAD_TYPES: dict[str, type] = {
    ON_SESSION_START: SessionStartPayload,
    ON_EXECUTION_RESULT: ExecutionResultPayload,
    ON_VERIFICATION_REPORT: VerificationReportPayload,
    ON_RESIDUAL_FOLLOWUP: ResidualFollowupPayload,
    ON_GOVERNANCE_CHECK: GovernanceCheckPayload,
    ON_SANDBOX_REQUIRED: SandboxRequiredPayload,
    ON_JOURNAL_APPEND: JournalAppendPayload,
}
