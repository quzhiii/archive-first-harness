from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import json
import unittest

from harness.context.context_engine import ContextEngine
from harness.governance.policy import GovernancePolicy
from harness.hooks.hook_orchestrator import HookDispatchError, HookOrchestrator
from harness.hooks.models import JournalAppendPayload
from harness.journal.learning_journal import LearningJournal
from harness.sandbox.rollback import RollbackManager
from harness.sandbox.sandbox_executor import SandboxExecutor
from harness.state.models import BudgetLevel, RiskLevel, TaskBlock, TaskContract, TaskType, WritePermissionLevel
from harness.state.state_manager import StateManager
from harness.tools.tool_discovery_service import ToolDiscoveryService
from runtime.executor import Executor
from runtime.orchestrator import Orchestrator
from runtime.verifier import Verifier


class FailingExecutor:
    def execute_step(self, step, available_tools, working_context):
        return {
            "status": "error",
            "tool_name": step.get("tool_name"),
            "output": None,
            "error": {
                "type": "execution_error",
                "message": "forced failure for journal event flow test",
            },
            "artifacts": [],
            "metadata": {"tool_input": dict(step.get("tool_input") or {})},
        }


def make_contract(
    *,
    task_type: TaskType = TaskType.RETRIEVAL,
    write_permission_level: WritePermissionLevel = WritePermissionLevel.READ,
    residual_risk_level: RiskLevel = RiskLevel.LOW,
    allowed_tools: list[str] | None = None,
) -> TaskContract:
    return TaskContract(
        contract_id=f"contract-{uuid4().hex}",
        goal="Run v0.3 journal event flow",
        success_criteria=["Produce a valid structured result."],
        allowed_tools=allowed_tools or ["search", "read_files"],
        stop_conditions=["Stop when the result is invalid."],
        expected_artifacts=["answer"],
        task_type=task_type,
        write_permission_level=write_permission_level,
        token_budget=BudgetLevel.LOW,
        latency_budget=BudgetLevel.LOW,
        uncertainty_level=RiskLevel.LOW,
        residual_risk_level=residual_risk_level,
        methodology_family="build" if task_type == TaskType.CODING else "research",
    )


class V03JournalEventFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / f"_tmp_v03_journal_{uuid4().hex}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.temp_dir, ignore_errors=True))
        self.state_manager = StateManager(self.temp_dir / "state")
        self.context_engine = ContextEngine()
        self.tool_discovery = ToolDiscoveryService()
        self.orchestrator = Orchestrator()
        self.verifier = Verifier()
        self.hooks = HookOrchestrator()
        self.governance_policy = GovernancePolicy()
        self.rollback_manager = RollbackManager()
        self.sandbox_executor = SandboxExecutor(self.rollback_manager)
        self.journal = LearningJournal(self.temp_dir / "learning_journal.jsonl")

    def _save_task(self, contract: TaskContract) -> None:
        self.state_manager.save_task_block(
            TaskBlock(
                task_id=contract.task_id,
                current_goal=contract.goal,
                contract_id=contract.contract_id,
                next_steps=["Run the journal event flow."],
            )
        )

    def _entry_for_task(self, task_id: str) -> dict[str, object]:
        for entry in self.journal.read_relevant_lessons(limit=20):
            if entry["task_id"] == task_id:
                return entry
        raise AssertionError(f"no lesson entry found for task_id {task_id}")

    def test_main_path_emits_on_journal_append_and_writes_lesson(self) -> None:
        captured: list[JournalAppendPayload] = []
        self.hooks.register("on_journal_append", captured.append)
        contract = make_contract()
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            learning_journal=self.journal,
            hook_orchestrator=self.hooks,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        self.assertEqual(len(captured), 1)
        payload = captured[0]
        self.assertTrue(payload.event_id)
        self.assertTrue(payload.timestamp)
        self.assertEqual(payload.task_id, contract.task_id)
        self.assertEqual(payload.contract_id, contract.contract_id)
        self.assertEqual(payload.schema_version, "v0.3")
        self.assertEqual(payload.source, payload.lesson_entry["source"])
        self.assertEqual(result["learning_journal"]["status"], "written")
        stored = self._entry_for_task(contract.task_id)
        self.assertEqual(stored["entry_id"], result["learning_journal"]["written_entry_id"])

    def test_success_and_failure_paths_both_generate_lessons(self) -> None:
        success_contract = make_contract(task_type=TaskType.RETRIEVAL)
        failure_contract = make_contract(task_type=TaskType.RETRIEVAL)
        self._save_task(success_contract)
        self._save_task(failure_contract)

        self.orchestrator.run(
            success_contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            learning_journal=self.journal,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )
        self.orchestrator.run(
            failure_contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            FailingExecutor(),
            verifier=self.verifier,
            learning_journal=self.journal,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        success_entry = self._entry_for_task(success_contract.task_id)
        failure_entry = self._entry_for_task(failure_contract.task_id)
        self.assertEqual(success_entry["source"], "success")
        self.assertEqual(failure_entry["source"], "failure")

    def test_sandbox_success_generates_compact_lesson_without_full_sandbox_result(self) -> None:
        contract = make_contract(
            task_type=TaskType.CODING,
            write_permission_level=WritePermissionLevel.WRITE,
            residual_risk_level=RiskLevel.LOW,
            allowed_tools=["edit_files"],
        )
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            learning_journal=self.journal,
            governance_policy=self.governance_policy,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        entry = self._entry_for_task(contract.task_id)
        serialized = json.dumps(entry, ensure_ascii=True)
        self.assertTrue(result["sandbox_triggered"])
        self.assertEqual(entry["source"], "sandbox")
        self.assertIn("sandbox_required", entry["tags"])
        self.assertIn("sandbox_success", entry["tags"])
        self.assertNotIn("snapshot_ref", serialized)
        self.assertNotIn("sandbox_result", serialized)
        self.assertNotIn("rollback_result", serialized)

    def test_sandbox_failure_with_rollback_generates_compact_lesson(self) -> None:
        contract = make_contract(
            task_type=TaskType.CODING,
            write_permission_level=WritePermissionLevel.WRITE,
            residual_risk_level=RiskLevel.HIGH,
            allowed_tools=["edit_files"],
        )
        self._save_task(contract)

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            FailingExecutor(),
            verifier=self.verifier,
            learning_journal=self.journal,
            governance_policy=self.governance_policy,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        entry = self._entry_for_task(contract.task_id)
        serialized = json.dumps(entry, ensure_ascii=True)
        self.assertEqual(result["rollback_result"]["status"], "rolled_back")
        self.assertEqual(entry["source"], "rollback")
        self.assertIn("rollback_triggered", entry["tags"])
        self.assertIn("sandbox_failed", entry["tags"])
        self.assertNotIn("restored_state", serialized)
        self.assertNotIn("snapshot_ref", serialized)
        self.assertNotIn("rollback_result", serialized)

    def test_lesson_entry_does_not_mix_state_summary_or_residual_payload(self) -> None:
        contract = make_contract()
        self._save_task(contract)

        self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            verifier=self.verifier,
            learning_journal=self.journal,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        entry = self._entry_for_task(contract.task_id)
        self.assertNotIn("current_goal", entry)
        self.assertNotIn("blockers", entry)
        self.assertNotIn("distilled_summary", entry)
        self.assertNotIn("residual_risk", entry)
        self.assertNotIn("state_writeback_payload", entry)

    def test_journal_packets_do_not_dominate_working_context(self) -> None:
        contract = make_contract(task_type=TaskType.RETRIEVAL)
        self._save_task(contract)
        for index in range(3):
            self.journal.append_lesson(
                self.journal.build_lesson_entry(
                    task_id=f"seed-{index}",
                    task_type=contract.task_type.value,
                    lesson=f"Reusable retrieval lesson {index}",
                    tags=["seeded"],
                )
            )

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            None,
            self.tool_discovery,
            Executor(),
            learning_journal=self.journal,
            sandbox_executor=self.sandbox_executor,
            rollback_manager=self.rollback_manager,
        )

        self.assertEqual(result["learning_journal"]["read_count"], 2)
        self.assertLessEqual(result["working_context_summary"]["retrieval_packet_count"], 2)
        self.assertGreaterEqual(result["working_context_summary"]["task_note_count"], 1)

    def test_journal_append_handler_failure_is_fail_fast_and_trace_visible(self) -> None:
        def fail_on_journal(payload: JournalAppendPayload) -> None:
            raise RuntimeError("journal append hook failed")

        self.hooks.register("on_journal_append", fail_on_journal)
        contract = make_contract()
        self._save_task(contract)

        with self.assertRaises(HookDispatchError):
            self.orchestrator.run(
                contract,
                self.state_manager,
                self.context_engine,
                None,
                self.tool_discovery,
                Executor(),
                verifier=self.verifier,
                learning_journal=self.journal,
                hook_orchestrator=self.hooks,
                sandbox_executor=self.sandbox_executor,
                rollback_manager=self.rollback_manager,
            )

        self.assertEqual(self.journal.read_relevant_lessons(limit=20), [])
        trace = self.hooks.get_recent_dispatches(limit=1)[0]
        self.assertEqual(trace["event_name"], "on_journal_append")
        self.assertEqual(trace["status"], "failed")
        self.assertEqual(trace["error_type"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
