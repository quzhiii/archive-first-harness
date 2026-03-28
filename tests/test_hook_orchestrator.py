from __future__ import annotations

from dataclasses import fields
import unittest

from harness.hooks.hook_orchestrator import HookDispatchError, HookOrchestrator
from harness.hooks.models import (
    EVENT_PAYLOAD_TYPES,
    FORBIDDEN_BULK_FIELD_NAMES,
    HOOK_EVENT_NAMES,
    HOOK_PAYLOAD_SCHEMA_VERSION,
    ExecutionResultPayload,
    GovernanceCheckPayload,
    JournalAppendPayload,
    ResidualFollowupPayload,
    SandboxRequiredPayload,
    SessionStartPayload,
    VerificationReportPayload,
)


class HookOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = HookOrchestrator()

    def test_can_register_handler(self) -> None:
        def handle(payload) -> None:
            return None

        self.orchestrator.register("on_session_start", handle)

        self.assertEqual(self.orchestrator.list_handlers("on_session_start"), ["handle"])

    def test_can_emit_specific_event(self) -> None:
        seen: list[str] = []

        def handle(payload: SessionStartPayload) -> str:
            seen.append(payload.task_id)
            return payload.contract_id

        payload = SessionStartPayload(
            task_id="task-1",
            contract_id="contract-1",
            task_type="coding",
            residual_risk_level="medium",
        )
        self.orchestrator.register("on_session_start", handle)
        results = self.orchestrator.emit("on_session_start", payload)

        self.assertEqual(seen, ["task-1"])
        self.assertEqual(results, ["contract-1"])

    def test_multiple_handlers_are_called(self) -> None:
        seen: list[str] = []

        def handle_one(payload: SessionStartPayload) -> None:
            seen.append(f"one:{payload.task_id}")

        def handle_two(payload: SessionStartPayload) -> None:
            seen.append(f"two:{payload.contract_id}")

        self.orchestrator.register("on_session_start", handle_one)
        self.orchestrator.register("on_session_start", handle_two)
        self.orchestrator.emit(
            "on_session_start",
            SessionStartPayload(
                task_id="task-1",
                contract_id="contract-2",
                task_type="coding",
                residual_risk_level="low",
            ),
        )

        self.assertEqual(seen, ["one:task-1", "two:contract-2"])

    def test_payload_is_passed_through_correctly(self) -> None:
        captured: list[ExecutionResultPayload] = []

        def handle(payload: ExecutionResultPayload) -> None:
            captured.append(payload)

        payload = ExecutionResultPayload(
            task_id="task-2",
            contract_id="contract-2",
            execution_result={"status": "success"},
            candidate_tools=[{"name": "read_file"}],
        )
        self.orchestrator.register("on_execution_result", handle)
        self.orchestrator.emit("on_execution_result", payload)

        self.assertIs(captured[0], payload)
        self.assertEqual(captured[0].candidate_tools[0]["name"], "read_file")

    def test_event_with_no_registered_handlers_returns_empty_result(self) -> None:
        results = self.orchestrator.emit(
            "on_governance_check",
            GovernanceCheckPayload(
                task_id="task-3",
                contract_id="contract-3",
                advice_summary={"selected_methodology": "debug"},
                governance_required=True,
            ),
        )

        self.assertEqual(results, [])

    def test_handler_errors_are_not_swallowed(self) -> None:
        def failing_handler(payload: SessionStartPayload) -> None:
            raise ValueError("boom")

        self.orchestrator.register("on_session_start", failing_handler)
        payload = SessionStartPayload(
            task_id="task-4",
            contract_id="contract-4",
            task_type="qa",
            residual_risk_level="medium",
        )

        with self.assertRaises(HookDispatchError) as context:
            self.orchestrator.emit("on_session_start", payload)

        self.assertIn("failing_handler", str(context.exception))
        self.assertIsInstance(context.exception.__cause__, ValueError)

    def test_list_handlers_without_event_is_clear(self) -> None:
        def first(payload) -> None:
            return None

        def second(payload) -> None:
            return None

        self.orchestrator.register("on_session_start", first)
        self.orchestrator.register("on_journal_append", second)
        listing = self.orchestrator.list_handlers()

        self.assertEqual(set(listing), HOOK_EVENT_NAMES)
        self.assertEqual(listing["on_session_start"], ["first"])
        self.assertEqual(listing["on_journal_append"], ["second"])

    def test_payload_type_mismatch_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.orchestrator.emit(
                "on_session_start",
                ExecutionResultPayload(
                    task_id="task-5",
                    contract_id="contract-5",
                    execution_result={"status": "success"},
                    candidate_tools=[],
                ),
            )

    def test_emit_records_dispatch_trace(self) -> None:
        def handle(payload: SessionStartPayload) -> None:
            return None

        payload = SessionStartPayload(
            task_id="task-6",
            contract_id="contract-6",
            task_type="coding",
            residual_risk_level="low",
        )
        self.orchestrator.register("on_session_start", handle)
        self.orchestrator.emit("on_session_start", payload)
        trace = self.orchestrator.get_recent_dispatches(limit=1)[0]

        self.assertEqual(trace["event_name"], "on_session_start")
        self.assertEqual(trace["event_id"], payload.event_id)
        self.assertEqual(trace["handler_count"], 1)
        self.assertEqual(trace["status"], "success")
        self.assertIsNone(trace["error_type"])
        self.assertEqual(trace["timestamp"], payload.timestamp)

    def test_failed_dispatch_is_visible_in_recent_dispatch_trace(self) -> None:
        def failing_handler(payload: SessionStartPayload) -> None:
            raise RuntimeError("dispatch failed")

        payload = SessionStartPayload(
            task_id="task-7",
            contract_id="contract-7",
            task_type="research",
            residual_risk_level="medium",
        )
        self.orchestrator.register("on_session_start", failing_handler)

        with self.assertRaises(HookDispatchError):
            self.orchestrator.emit("on_session_start", payload)

        trace = self.orchestrator.get_recent_dispatches(limit=1)[0]
        self.assertEqual(trace["status"], "failed")
        self.assertEqual(trace["error_type"], "RuntimeError")
        self.assertEqual(trace["event_id"], payload.event_id)

    def test_get_recent_dispatches_limit_is_clear(self) -> None:
        def handle(payload: SessionStartPayload) -> None:
            return None

        self.orchestrator.register("on_session_start", handle)
        for index in range(3):
            self.orchestrator.emit(
                "on_session_start",
                SessionStartPayload(
                    task_id=f"task-{index}",
                    contract_id=f"contract-{index}",
                    task_type="coding",
                    residual_risk_level="low",
                ),
            )

        recent = self.orchestrator.get_recent_dispatches(limit=2)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[-1]["event_name"], "on_session_start")

    def test_payload_models_have_unified_base_fields(self) -> None:
        base_fields = {"event_id", "timestamp", "task_id", "contract_id", "schema_version"}
        for payload_type in EVENT_PAYLOAD_TYPES.values():
            self.assertTrue(base_fields.issubset({field.name for field in fields(payload_type)}))

    def test_payload_models_do_not_expose_bulk_dump_fields(self) -> None:
        for payload_type in EVENT_PAYLOAD_TYPES.values():
            payload_fields = {field.name for field in fields(payload_type)}
            self.assertTrue(payload_fields.isdisjoint(FORBIDDEN_BULK_FIELD_NAMES))

    def test_minimal_payload_instances_can_be_constructed(self) -> None:
        payloads = [
            SessionStartPayload(
                task_id="task-1",
                contract_id="contract-1",
                task_type="coding",
                residual_risk_level="low",
            ),
            ExecutionResultPayload(
                task_id="task-2",
                contract_id="contract-2",
                execution_result={"status": "success"},
                candidate_tools=[],
            ),
            VerificationReportPayload(
                task_id="task-3",
                contract_id="contract-3",
                verification_report={"passed": True},
                residual_risk_hint="low",
            ),
            ResidualFollowupPayload(
                task_id="task-4",
                contract_id="contract-4",
                residual_reassessment={"reassessed_level": "high"},
            ),
            GovernanceCheckPayload(
                task_id="task-5",
                contract_id="contract-5",
                advice_summary={"summary": "needs review"},
                governance_required=True,
            ),
            SandboxRequiredPayload(
                task_id="task-6",
                action="write_file",
                risk_level="high",
                write_permission_level="write",
            ),
            JournalAppendPayload(
                task_id="task-7",
                lesson_entry={"entry_id": "lesson-1"},
                source="success",
            ),
        ]

        self.assertEqual(len(payloads), 7)
        self.assertEqual(payloads[0].contract_id, "contract-1")
        self.assertIsNone(payloads[-1].contract_id)
        self.assertTrue(all(payload.event_id for payload in payloads))
        self.assertTrue(all(payload.timestamp for payload in payloads))
        self.assertTrue(all(payload.schema_version == HOOK_PAYLOAD_SCHEMA_VERSION for payload in payloads))

    def test_event_id_is_unique_per_payload_instance(self) -> None:
        first = SessionStartPayload(
            task_id="task-8",
            contract_id="contract-8",
            task_type="coding",
            residual_risk_level="low",
        )
        second = SessionStartPayload(
            task_id="task-8",
            contract_id="contract-8",
            task_type="coding",
            residual_risk_level="low",
        )

        self.assertNotEqual(first.event_id, second.event_id)

    def test_schema_version_is_fixed_to_v03(self) -> None:
        with self.assertRaises(ValueError):
            SessionStartPayload(
                task_id="task-9",
                contract_id="contract-9",
                task_type="coding",
                residual_risk_level="low",
                schema_version="v0.4",
            )


if __name__ == "__main__":
    unittest.main()
