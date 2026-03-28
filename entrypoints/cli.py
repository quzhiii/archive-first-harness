from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from pathlib import Path
import sys
from typing import Any

from entrypoints.settings import load_settings
from harness.context.context_engine import ContextEngine
from harness.evaluation.realm_evaluator import RealmEvaluator
from harness.state.models import TaskBlock
from harness.state.state_manager import StateManager
from harness.telemetry.metrics import MetricsAggregator
from harness.telemetry.tracer import Tracer
from harness.tools.tool_discovery_service import ToolDiscoveryService
from planner.task_contract_builder import TaskContractBuilder
from runtime.executor import Executor
from runtime.orchestrator import Orchestrator
from runtime.verifier import Verifier


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = load_settings()

    try:
        if args.command == "run":
            task_text = _resolve_task_text(args)
            result = run_command(task_text, settings)
            _print_json(result)
            return 0 if _run_succeeded(result) else 1

        if args.command == "inspect-state":
            _print_json(inspect_state_command(settings))
            return 0

        if args.command == "inspect-contract":
            _print_json(inspect_contract_command(settings))
            return 0

        raise ValueError(f"unsupported command: {args.command}")
    except Exception as exc:
        print(f"CLI error: {exc}", file=sys.stderr)
        return 1


def run_command(task_text: str, settings) -> dict[str, Any]:
    artifacts_dir = settings.artifacts_dir
    state_dir = artifacts_dir / "state"
    contracts_dir = artifacts_dir / "contracts"
    state_dir.mkdir(parents=True, exist_ok=True)
    contracts_dir.mkdir(parents=True, exist_ok=True)

    builder = TaskContractBuilder()
    task_contract = builder.build(
        task_text,
        constraints={
            "token_budget": settings.default_token_budget,
            "latency_budget": settings.default_latency_budget,
        },
    )
    _write_json(contracts_dir / "latest_contract.json", _to_json_value(task_contract))

    state_manager = StateManager(state_dir)
    state_manager.save_task_block(
        TaskBlock(
            task_id=task_contract.task_id,
            current_goal=task_contract.goal,
            contract_id=task_contract.contract_id,
            next_steps=["Execute the v0.1 main path."],
        )
    )

    context_engine = ContextEngine()
    tool_discovery_service = ToolDiscoveryService()
    executor = Executor()
    orchestrator = Orchestrator()
    verifier = Verifier()
    tracer = Tracer()
    metrics = MetricsAggregator()
    evaluator = RealmEvaluator()

    tracer.record_event(
        "run_started",
        {"task_id": task_contract.task_id, "contract_id": task_contract.contract_id},
    )
    orchestrator_result = orchestrator.run(
        task_contract,
        state_manager,
        context_engine,
        None,
        tool_discovery_service,
        executor,
    )
    verification_report = verifier.verify_execution_result(
        orchestrator_result["execution_result"],
        task_contract,
    )
    tracer.record_event(
        "run_finished",
        {
            "task_id": task_contract.task_id,
            "contract_id": task_contract.contract_id,
            "execution_status": orchestrator_result["execution_result"]["status"],
            "verification_status": verification_report["status"],
        },
    )

    if settings.telemetry_enabled:
        working_context_summary = orchestrator_result["working_context_summary"]
        tracer.record_metric("token_count", 0)
        tracer.record_metric("latency_ms", 0)
        tracer.record_metric("cost_estimate", 0)
        tracer.record_metric("retry_count", 0)
        tracer.record_metric("rollback_count", 0)
        tracer.record_metric("tool_misuse_count", 0)
        tracer.record_metric(
            "execution_failure_count",
            1 if orchestrator_result["execution_result"]["status"] != "success" else 0,
        )
        tracer.record_metric(
            "context_size",
            working_context_summary["task_note_count"]
            + working_context_summary["project_note_count"]
            + working_context_summary["global_note_count"],
        )
        if orchestrator_result["selected_skills"]:
            tracer.record_metric("skill_hit_rate", 1)
        tracer.record_metric("human_handoff_count", 0)

    trace = tracer.get_trace()
    metrics_summary = metrics.aggregate(trace)
    evaluation = evaluator.evaluate(metrics_summary)

    return {
        "task_contract": orchestrator_result["task_contract"],
        "working_context_summary": orchestrator_result["working_context_summary"],
        "selected_skills": orchestrator_result["selected_skills"],
        "candidate_tools": orchestrator_result["candidate_tools"],
        "execution_plan": orchestrator_result["execution_plan"],
        "execution_result": orchestrator_result["execution_result"],
        "verification_report": verification_report,
        "telemetry": metrics_summary,
        "evaluation": evaluation,
        "state_writeback_payload": orchestrator_result["state_writeback_payload"],
        "verifier_handoff": orchestrator_result["verifier_handoff"],
    }


def inspect_state_command(settings) -> dict[str, Any]:
    state_dir = settings.artifacts_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    state_files = sorted(state_dir.glob("*.json"))
    summaries: list[dict[str, Any]] = []
    for path in state_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        summaries.append(
            {
                "name": path.name,
                "version": payload.get("version", 0),
                "data_keys": sorted(payload.get("data", {}).keys()),
            }
        )

    return {
        "status": "ok",
        "artifacts_dir": str(settings.artifacts_dir),
        "state_dir": str(state_dir),
        "state_file_count": len(summaries),
        "state_files": summaries,
    }


def inspect_contract_command(settings) -> dict[str, Any]:
    contract_path = settings.artifacts_dir / "contracts" / "latest_contract.json"
    if not contract_path.exists():
        raise FileNotFoundError("no latest contract has been recorded yet")

    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    return {
        "status": "ok",
        "contract_path": str(contract_path),
        "contract": payload,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal CLI for the B v0.1 runtime harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the minimal main path")
    run_parser.add_argument("task", nargs="*", help="Task description to run")

    subparsers.add_parser("inspect-state", help="Inspect persisted state summary")
    subparsers.add_parser("inspect-contract", help="Inspect the latest contract summary")
    return parser


def _resolve_task_text(args) -> str:
    if args.task:
        return " ".join(args.task).strip()

    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if text:
            return text

    raise ValueError("run requires a task description as an argument or stdin")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))


def _run_succeeded(result: dict[str, Any]) -> bool:
    execution_ok = result["execution_result"]["status"] == "success"
    verification_ok = result["verification_report"]["passed"]
    return execution_ok and verification_ok


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _to_json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
