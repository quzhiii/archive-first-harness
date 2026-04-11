from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from entrypoints.archive_browse import (
    browse_run_archives,
    compare_run_archives,
    find_run_archive,
    format_archive_brief,
    read_latest_run_archive,
)
from entrypoints.batch_export import BatchExportOptions, export_batch_results
from entrypoints.batch_runner import load_batch_request_file, run_batch_request
from entrypoints.demo_flow import ensure_demo_archives, format_demo_brief
from entrypoints.history_browse import (
    browse_run_history,
    find_run_history_entry,
    format_history_brief,
    get_latest_run_id,
    get_latest_run_output_dir,
    read_latest_run,
    read_run_history_summary,
)
from entrypoints.history_summary import (
    write_latest_run_pointer,
    write_run_history_summary,
)
from entrypoints.run_history import append_run_history_entry
from entrypoints.settings import load_settings
from entrypoints.task_runner import (
    SurfaceTaskRequest,
    run_task_request,
    surface_result_succeeded,
)
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
                    history_file=_build_batch_history_file(args),
                    write_history_summary=bool(args.write_history_summary),
                    history_summary_limit=_build_history_summary_limit(args),
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

        if args.command == "history":
            _validate_history_args(args)
            print(
                history_command(
                    settings,
                    history_file=args.history_file,
                    latest=bool(args.latest),
                    summary=bool(args.summary),
                    last_id=bool(args.last_id),
                    last_output_dir=bool(args.last_output_dir),
                    run_id=args.run_id,
                    limit=args.limit,
                )
            )
            return 0

        if args.command == "archive":
            _validate_archive_args(args)
            print(
                archive_command(
                    settings,
                    archive_root=args.archive_root,
                    latest=bool(args.latest),
                    run_id=args.run_id,
                    compare_run_ids=list(args.compare_run_id or []),
                    workflow_profile_id=args.workflow_profile_id,
                    task_type=args.task_type,
                    formation_id=args.formation_id,
                    status=args.status,
                    failure_class=args.failure_class,
                    limit=args.limit,
                )
            )
            return 0

        if args.command == "demo":
            print(
                demo_command(
                    settings,
                    archive_root=args.archive_root,
                )
            )
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
    history_file: str | None = None,
    write_history_summary: bool = False,
    history_summary_limit: int = 20,
) -> dict[str, Any]:
    request = load_batch_request_file(
        batch_file,
        batch_name=batch_name,
        stop_on_error=stop_on_error,
    )
    result = run_batch_request(request, settings)
    if export_options is None:
        if history_file:
            raise ValueError("--history-file requires batch export to be enabled")
        if write_history_summary:
            raise ValueError("history summary requires batch export to be enabled")
        return result

    output = dict(result)
    export_result = export_batch_results(result, export_options)
    output["artifacts_export"] = export_result
    history_result = append_run_history_entry(
        result, export_result, history_file=history_file
    )
    output["run_history"] = history_result
    history_index: dict[str, Any] = {
        "latest_run": write_latest_run_pointer(history_result["history_file"]),
    }
    if write_history_summary:
        history_index["history_summary"] = write_run_history_summary(
            history_result["history_file"],
            limit=history_summary_limit,
        )
    output["history_index"] = history_index
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


def history_command(
    settings,
    *,
    history_file: str | None = None,
    latest: bool = False,
    summary: bool = False,
    last_id: bool = False,
    last_output_dir: bool = False,
    run_id: str | None = None,
    limit: int | None = None,
) -> str:
    resolved_history_file = str(
        history_file or (settings.artifacts_dir / "run_history.jsonl")
    )
    if last_id:
        return get_latest_run_id(resolved_history_file)
    if last_output_dir:
        return get_latest_run_output_dir(resolved_history_file)
    if run_id:
        payload = find_run_history_entry(resolved_history_file, run_id)
        return format_history_brief(payload)
    if latest:
        payload = read_latest_run(resolved_history_file)
        return format_history_brief(payload)

    effective_limit = 10 if limit is None else int(limit)
    if summary:
        payload = read_run_history_summary(resolved_history_file, limit=effective_limit)
        return format_history_brief(payload)

    payload = browse_run_history(resolved_history_file, limit=effective_limit)
    return format_history_brief(payload)


def archive_command(
    settings,
    *,
    archive_root: str | None = None,
    latest: bool = False,
    run_id: str | None = None,
    compare_run_ids: list[str] | None = None,
    workflow_profile_id: str | None = None,
    task_type: str | None = None,
    formation_id: str | None = None,
    status: str | None = None,
    failure_class: str | None = None,
    limit: int | None = None,
) -> str:
    resolved_archive_root = str(archive_root or (settings.artifacts_dir / "runs"))
    if latest:
        payload = read_latest_run_archive(resolved_archive_root)
        return format_archive_brief(payload)

    compare_values = [item for item in (compare_run_ids or []) if str(item).strip()]
    if len(compare_values) == 2:
        payload = compare_run_archives(
            resolved_archive_root, compare_values[0], compare_values[1]
        )
        return format_archive_brief(payload)
    if compare_values:
        raise ValueError("--compare-run-id must be provided exactly twice")
    if run_id:
        payload = find_run_archive(resolved_archive_root, run_id)
        return format_archive_brief(payload)

    effective_limit = 10 if limit is None else int(limit)
    payload = browse_run_archives(
        resolved_archive_root,
        limit=effective_limit,
        workflow_profile_id=workflow_profile_id,
        task_type=task_type,
        formation_id=formation_id,
        status=status,
        failure_class=failure_class,
    )
    return format_archive_brief(payload)


def demo_command(
    settings,
    *,
    archive_root: str | None = None,
) -> str:
    payload = ensure_demo_archives(settings, archive_root=archive_root)
    return format_demo_brief(payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Minimal CLI for the profile-aware runtime harness"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="Run a single task through the minimal surface"
    )
    run_parser.add_argument("task_parts", nargs="*", help="Task description to run")
    run_parser.add_argument("--task", dest="task_text", help="Task description to run")
    run_parser.add_argument(
        "--batch-file",
        dest="batch_file",
        help="Path to a batch json/jsonl request file",
    )
    run_parser.add_argument(
        "--batch-name", dest="batch_name", help="Optional batch name override"
    )
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
        "--history-file",
        dest="history_file",
        help="Optional run history manifest file path. Defaults to <output-dir>/run_history.jsonl.",
    )
    run_parser.add_argument(
        "--write-history-summary",
        dest="write_history_summary",
        action="store_true",
        help="Write a compact run history summary json derived from the manifest.",
    )
    run_parser.add_argument(
        "--history-summary-limit",
        dest="history_summary_limit",
        type=int,
        help="Optional recent-entry limit for run_history_summary.json. Defaults to 20 when enabled.",
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
    run_parser.add_argument(
        "--task-type", dest="task_type", help="Optional task type override"
    )
    run_parser.add_argument(
        "--workflow-profile-id",
        dest="workflow_profile_id",
        help="Canonical workflow profile id",
    )
    run_parser.add_argument(
        "--workflow-profile", dest="workflow_profile", help="Workflow profile alias"
    )
    run_parser.add_argument(
        "--mission-profile-id", dest="mission_profile_id", help="Mission profile alias"
    )
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
    subparsers.add_parser(
        "inspect-contract", help="Inspect the latest contract summary"
    )

    history_parser = subparsers.add_parser(
        "history", help="Browse recent run history artifacts"
    )
    history_parser.add_argument(
        "--history-file",
        dest="history_file",
        help="Path to run_history.jsonl. Defaults to <artifacts-dir>/run_history.jsonl.",
    )
    history_parser.add_argument(
        "--latest",
        dest="latest",
        action="store_true",
        help="Show the latest run pointer or manifest-derived latest run.",
    )
    history_parser.add_argument(
        "--summary",
        dest="summary",
        action="store_true",
        help="Show recent run history summary entries.",
    )
    history_parser.add_argument(
        "--limit",
        dest="limit",
        type=int,
        help="Optional recent-entry limit for history browsing. Defaults to 10.",
    )
    history_parser.add_argument(
        "--last-id",
        dest="last_id",
        action="store_true",
        help="Print only the latest run_id.",
    )
    history_parser.add_argument(
        "--last-output-dir",
        dest="last_output_dir",
        action="store_true",
        help="Print only the latest output_dir.",
    )
    history_parser.add_argument(
        "--run-id",
        dest="run_id",
        help="Show a minimal summary for one exact run_id match.",
    )

    archive_parser = subparsers.add_parser(
        "archive", help="Browse per-run diagnostic archives"
    )
    archive_parser.add_argument(
        "--archive-root",
        dest="archive_root",
        help="Path to artifacts/runs. Defaults to <artifacts-dir>/runs.",
    )
    archive_parser.add_argument(
        "--latest",
        dest="latest",
        action="store_true",
        help="Show the latest archive entry.",
    )
    archive_parser.add_argument(
        "--run-id",
        dest="run_id",
        help="Show a diagnostic summary for one exact archive run_id match.",
    )
    archive_parser.add_argument(
        "--compare-run-id",
        dest="compare_run_id",
        action="append",
        help="Compare two archive run ids. Repeat exactly twice.",
    )
    archive_parser.add_argument(
        "--workflow-profile-id",
        dest="workflow_profile_id",
        help="Filter archive summary by workflow profile id.",
    )
    archive_parser.add_argument(
        "--task-type",
        dest="task_type",
        help="Filter archive summary by task type.",
    )
    archive_parser.add_argument(
        "--formation-id",
        dest="formation_id",
        help="Filter archive summary by formation id.",
    )
    archive_parser.add_argument(
        "--status",
        dest="status",
        help="Filter archive summary by status.",
    )
    archive_parser.add_argument(
        "--failure-class",
        dest="failure_class",
        help="Filter archive summary by failure class.",
    )
    archive_parser.add_argument(
        "--limit",
        dest="limit",
        type=int,
        help="Optional recent-entry limit for archive browsing. Defaults to 10.",
    )

    demo_parser = subparsers.add_parser(
        "demo",
        help="Create deterministic demo archives for archive browse/compare onboarding",
    )
    demo_parser.add_argument(
        "--archive-root",
        dest="archive_root",
        help="Optional path to artifacts/runs. Defaults to <artifacts-dir>/runs.",
    )
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

    raise ValueError(
        "run requires a task description via --task, positional args, or stdin"
    )


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))


def _result_succeeded(args, result: dict[str, Any]) -> bool:
    if getattr(args, "batch_file", None):
        return int(result.get("failed_tasks", 0) or 0) == 0
    return surface_result_succeeded(result)


def _build_batch_export_options(args) -> BatchExportOptions | None:
    output_dir = getattr(args, "output_dir", None)
    history_file = getattr(args, "history_file", None)
    write_history_summary = bool(getattr(args, "write_history_summary", False))
    history_summary_limit = getattr(args, "history_summary_limit", None)
    export_json = bool(getattr(args, "export_json", False))
    export_jsonl = bool(getattr(args, "export_jsonl", False))
    export_md = bool(getattr(args, "export_md", False))
    has_explicit_formats = export_json or export_jsonl or export_md

    if not output_dir:
        if has_explicit_formats:
            raise ValueError("export format flags require --output-dir")
        if history_file:
            raise ValueError("--history-file requires --output-dir")
        if write_history_summary or history_summary_limit is not None:
            raise ValueError("history summary flags require --output-dir")
        return None

    if has_explicit_formats:
        return BatchExportOptions(
            output_dir=output_dir,
            write_json=export_json,
            write_jsonl=export_jsonl,
            write_markdown_summary=export_md,
        )

    return BatchExportOptions(output_dir=output_dir)


def _build_batch_history_file(args) -> str | None:
    history_file = getattr(args, "history_file", None)
    if history_file:
        return str(history_file)
    if getattr(args, "output_dir", None):
        return None
    return None


def _build_history_summary_limit(args) -> int:
    write_history_summary = bool(getattr(args, "write_history_summary", False))
    history_summary_limit = getattr(args, "history_summary_limit", None)
    if history_summary_limit is not None and not write_history_summary:
        raise ValueError("--history-summary-limit requires --write-history-summary")
    if not write_history_summary:
        return 20
    if history_summary_limit is None:
        return 20
    if history_summary_limit < 0:
        raise ValueError("--history-summary-limit must be non-negative")
    return int(history_summary_limit)


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
            raise ValueError(
                f"--batch-file cannot be combined with --{field_name.replace('_', '-')}"
            )


def _validate_single_run_args(args) -> None:
    for field_name in (
        "output_dir",
        "history_file",
        "write_history_summary",
        "history_summary_limit",
        "export_json",
        "export_jsonl",
        "export_md",
        "batch_name",
        "stop_on_error",
    ):
        value = getattr(args, field_name, None)
        if value:
            raise ValueError(
                f"--{field_name.replace('_', '-')} is only supported with --batch-file"
            )


def _validate_history_args(args) -> None:
    mode_count = sum(
        1
        for item in (
            bool(getattr(args, "latest", False)),
            bool(getattr(args, "summary", False)),
            bool(getattr(args, "last_id", False)),
            bool(getattr(args, "last_output_dir", False)),
            bool(getattr(args, "run_id", None)),
        )
        if item
    )
    if mode_count > 1:
        raise ValueError("history mode flags are mutually exclusive")
    limit = getattr(args, "limit", None)
    if limit is not None and limit < 0:
        raise ValueError("--limit must be non-negative")
    if (
        any(
            (
                bool(getattr(args, "latest", False)),
                bool(getattr(args, "last_id", False)),
                bool(getattr(args, "last_output_dir", False)),
                bool(getattr(args, "run_id", None)),
            )
        )
        and limit is not None
    ):
        raise ValueError("--limit is only used with summary/browse modes")


def _validate_archive_args(args) -> None:
    limit = getattr(args, "limit", None)
    if limit is not None and limit < 0:
        raise ValueError("--limit must be non-negative")

    latest = bool(getattr(args, "latest", False))
    compare_run_ids = [
        item
        for item in list(getattr(args, "compare_run_id", None) or [])
        if str(item).strip()
    ]
    run_id = getattr(args, "run_id", None)

    if latest and run_id:
        raise ValueError("--latest cannot be combined with --run-id")
    if latest and compare_run_ids:
        raise ValueError("--latest cannot be combined with --compare-run-id")
    if run_id and compare_run_ids:
        raise ValueError("--run-id cannot be combined with --compare-run-id")
    if compare_run_ids and len(compare_run_ids) != 2:
        raise ValueError("--compare-run-id must be provided exactly twice")
    if compare_run_ids and any(
        (
            getattr(args, "workflow_profile_id", None),
            getattr(args, "task_type", None),
            getattr(args, "formation_id", None),
            getattr(args, "status", None),
            getattr(args, "failure_class", None),
            limit is not None,
        )
    ):
        raise ValueError(
            "compare mode cannot be combined with browse filters or --limit"
        )
    if (latest or run_id) and any(
        (
            getattr(args, "task_type", None),
            getattr(args, "formation_id", None),
            limit is not None,
        )
    ):
        raise ValueError(
            "--task-type, --formation-id, and --limit are only used with archive browse mode"
        )


if __name__ == "__main__":
    raise SystemExit(main())
