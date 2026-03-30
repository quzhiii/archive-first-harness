from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from entrypoints.batch_export import BatchExportOptions, export_batch_results
from entrypoints.batch_runner import load_batch_request_file, run_batch_request
from entrypoints.settings import load_settings
from entrypoints.task_runner import SurfaceTaskRequest, run_task_request, surface_result_succeeded
from runtime.executor import Executor



def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = load_settings()

    try:
        if args.command == "run":
            if args.batch_file:
                _validate_batch_run_args(args)
                result = run_batch_command(
                    args.batch_file,
                    settings,
                    batch_name=args.batch_name,
                    stop_on_error=True if args.stop_on_error else None,
                    export_options=_build_batch_export_options(args),
                )
            else:
                _validate_single_run_args(args)
                task_text = _resolve_task_text(args)
                result = run_command(
                    task_text,
                    settings,
                    task_type=args.task_type,
                    workflow_profile_id=args.workflow_profile_id,
                    workflow_profile=args.workflow_profile,
                    mission_profile_id=args.mission_profile_id,
                    success_criteria=list(args.success_criteria or []),
                    expected_artifacts=list(args.expected_artifacts or []),
                )
            _print_json(result)
            return 0 if _result_succeeded(args, result) else 1

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



def run_command(
    task_text: str,
    settings,
    *,
    task_type: str | None = None,
    workflow_profile_id: str | None = None,
    workflow_profile: str | None = None,
    mission_profile_id: str | None = None,
    constraints: dict[str, Any] | None = None,
    success_criteria: list[str] | None = None,
    expected_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    request = SurfaceTaskRequest(
        task=task_text,
        task_type=task_type,
        workflow_profile_id=workflow_profile_id,
        workflow_profile=workflow_profile,
        mission_profile_id=mission_profile_id,
        constraints=dict(constraints or {}),
        success_criteria=list(success_criteria or []),
        expected_artifacts=list(expected_artifacts or []),
    )
    return run_task_request(request, settings, executor=Executor())



def run_batch_command(
    batch_file: str,
    settings,
    *,
    batch_name: str | None = None,
    stop_on_error: bool | None = None,
    export_options: BatchExportOptions | dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = load_batch_request_file(
        batch_file,
        batch_name=batch_name,
        stop_on_error=stop_on_error,
    )
    result = run_batch_request(request, settings)
    if export_options is None:
        return result

    output = dict(result)
    output["artifacts_export"] = export_batch_results(result, export_options)
    return output



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
    parser = argparse.ArgumentParser(description="Minimal CLI for the profile-aware runtime harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a single task through the minimal surface")
    run_parser.add_argument("task_parts", nargs="*", help="Task description to run")
    run_parser.add_argument("--task", dest="task_text", help="Task description to run")
    run_parser.add_argument("--batch-file", dest="batch_file", help="Path to a batch json/jsonl request file")
    run_parser.add_argument("--batch-name", dest="batch_name", help="Optional batch name override")
    run_parser.add_argument(
        "--stop-on-error",
        dest="stop_on_error",
        action="store_true",
        help="Stop a batch after the first failed task",
    )
    run_parser.add_argument(
        "--output-dir",
        dest="output_dir",
        help="Output directory for exported batch artifacts",
    )
    run_parser.add_argument(
        "--export-json",
        dest="export_json",
        action="store_true",
        help="Export a full batch result json snapshot",
    )
    run_parser.add_argument(
        "--export-jsonl",
        dest="export_jsonl",
        action="store_true",
        help="Export line-oriented per-task batch results",
    )
    run_parser.add_argument(
        "--export-md",
        dest="export_md",
        action="store_true",
        help="Export a minimal markdown batch summary",
    )
    run_parser.add_argument("--task-type", dest="task_type", help="Optional task type override")
    run_parser.add_argument("--workflow-profile-id", dest="workflow_profile_id", help="Canonical workflow profile id")
    run_parser.add_argument("--workflow-profile", dest="workflow_profile", help="Workflow profile alias")
    run_parser.add_argument("--mission-profile-id", dest="mission_profile_id", help="Mission profile alias")
    run_parser.add_argument(
        "--success-criteria",
        dest="success_criteria",
        action="append",
        help="Optional success criterion. Repeat to provide multiple items.",
    )
    run_parser.add_argument(
        "--expected-artifact",
        dest="expected_artifacts",
        action="append",
        help="Optional expected artifact. Repeat to provide multiple items.",
    )

    subparsers.add_parser("inspect-state", help="Inspect persisted state summary")
    subparsers.add_parser("inspect-contract", help="Inspect the latest contract summary")
    return parser



def _resolve_task_text(args) -> str:
    if getattr(args, "task_text", None):
        return str(args.task_text).strip()

    task_parts = getattr(args, "task_parts", None)
    if task_parts:
        return " ".join(task_parts).strip()

    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if text:
            return text

    raise ValueError("run requires a task description via --task, positional args, or stdin")



def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))



def _result_succeeded(args, result: dict[str, Any]) -> bool:
    if getattr(args, "batch_file", None):
        return int(result.get("failed_tasks", 0) or 0) == 0
    return surface_result_succeeded(result)



def _build_batch_export_options(args) -> BatchExportOptions | None:
    output_dir = getattr(args, "output_dir", None)
    export_json = bool(getattr(args, "export_json", False))
    export_jsonl = bool(getattr(args, "export_jsonl", False))
    export_md = bool(getattr(args, "export_md", False))
    has_explicit_formats = export_json or export_jsonl or export_md

    if not output_dir:
        if has_explicit_formats:
            raise ValueError("export format flags require --output-dir")
        return None

    if has_explicit_formats:
        return BatchExportOptions(
            output_dir=output_dir,
            write_json=export_json,
            write_jsonl=export_jsonl,
            write_markdown_summary=export_md,
        )

    return BatchExportOptions(output_dir=output_dir)



def _validate_batch_run_args(args) -> None:
    if getattr(args, "task_text", None):
        raise ValueError("--batch-file cannot be combined with --task")
    if getattr(args, "task_parts", None):
        raise ValueError("--batch-file cannot be combined with positional task text")
    for field_name in (
        "task_type",
        "workflow_profile_id",
        "workflow_profile",
        "mission_profile_id",
        "success_criteria",
        "expected_artifacts",
    ):
        value = getattr(args, field_name, None)
        if value:
            raise ValueError(f"--batch-file cannot be combined with --{field_name.replace('_', '-')}")



def _validate_single_run_args(args) -> None:
    for field_name in ("output_dir", "export_json", "export_jsonl", "export_md", "batch_name", "stop_on_error"):
        value = getattr(args, field_name, None)
        if value:
            raise ValueError(f"--{field_name.replace('_', '-')} is only supported with --batch-file")


if __name__ == "__main__":
    raise SystemExit(main())
