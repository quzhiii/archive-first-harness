from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import unittest

from harness.context.context_engine import ContextEngine
from harness.state.models import TaskBlock
from harness.state.state_manager import StateManager
from harness.tools.tool_discovery_service import ToolDiscoveryService
from planner.task_contract_builder import TaskContractBuilder
from runtime.executor import Executor
from runtime.orchestrator import Orchestrator


class SpyContextEngine(ContextEngine):
    def __init__(self) -> None:
        super().__init__()
        self.called = False

    def build_working_context(self, *args, **kwargs):
        self.called = True
        return super().build_working_context(*args, **kwargs)


class SpyToolDiscoveryService(ToolDiscoveryService):
    def __init__(self) -> None:
        super().__init__()
        self.list_called = False
        self.schema_requests: list[str] = []

    def list_candidate_tools(self, task_type: str, allowed_tools: list[str] | None = None):
        self.list_called = True
        return super().list_candidate_tools(task_type, allowed_tools)

    def get_tool_schema(self, tool_name: str):
        self.schema_requests.append(tool_name)
        return super().get_tool_schema(tool_name)


class SpyExecutor(Executor):
    def __init__(self) -> None:
        self.called = False

    def execute_step(self, step, available_tools, working_context):
        self.called = True
        return super().execute_step(step, available_tools, working_context)


class StubSkillLoader:
    def __init__(self) -> None:
        self.called = False

    def load_for_task(self, task_contract, working_context):
        self.called = True
        return ["structured-task-execution"]


class OrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_dir = Path("tests") / f"_tmp_orchestrator_{uuid4().hex}"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: rmtree(self.storage_dir, ignore_errors=True))
        self.builder = TaskContractBuilder()
        self.orchestrator = Orchestrator()
        self.state_manager = StateManager(self.storage_dir)
        self.context_engine = SpyContextEngine()
        self.tool_discovery_service = SpyToolDiscoveryService()
        self.executor = SpyExecutor()
        self.skill_loader = StubSkillLoader()

    def test_run_executes_minimal_main_path(self) -> None:
        contract = self.builder.build("Implement the runtime orchestrator execution path.")
        self.state_manager.save_task_block(
            TaskBlock(task_id=contract.contract_id, current_goal=contract.goal)
        )

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            self.skill_loader,
            self.tool_discovery_service,
            self.executor,
        )

        self.assertTrue(self.context_engine.called)
        self.assertTrue(self.skill_loader.called)
        self.assertTrue(self.tool_discovery_service.list_called)
        self.assertGreater(len(self.tool_discovery_service.schema_requests), 0)
        self.assertTrue(self.executor.called)
        self.assertEqual(result["execution_result"]["status"], "success")
        self.assertEqual(result["worker_mode"], "single")
        self.assertEqual(result["spawned_workers"], 0)
        self.assertIn("state_writeback_payload", result)
        self.assertIn("verifier_handoff", result)
        self.assertEqual(result["selected_skills"], ["structured-task-execution"])

    def test_run_builds_working_context_before_execution_and_uses_tool_discovery(self) -> None:
        contract = self.builder.build("Fix the executor output formatting bug.")

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            self.skill_loader,
            self.tool_discovery_service,
            self.executor,
        )

        self.assertGreater(result["working_context_summary"]["task_note_count"], 0)
        self.assertGreater(len(result["candidate_tools"]), 0)
        self.assertTrue(all("schema" not in tool for tool in result["candidate_tools"]))
        self.assertIsNotNone(result["execution_result"]["tool_name"])

    def test_run_returns_explicit_failure_when_no_tools_are_available(self) -> None:
        contract = self.builder.build(
            "Implement a change with unavailable tools only.",
            constraints={"allowed_tools": ["nonexistent_tool"]},
        )

        result = self.orchestrator.run(
            contract,
            self.state_manager,
            self.context_engine,
            self.skill_loader,
            self.tool_discovery_service,
            self.executor,
        )

        self.assertEqual(result["candidate_tools"], [])
        self.assertEqual(result["execution_result"]["status"], "error")
        self.assertEqual(result["execution_result"]["error"]["type"], "no_candidate_tools")
        self.assertFalse(self.executor.called)


if __name__ == "__main__":
    unittest.main()
