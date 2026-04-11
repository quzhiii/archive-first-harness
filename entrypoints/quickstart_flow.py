from __future__ import annotations

from pathlib import Path
import sys


def ensure_repo_root_on_sys_path(repo_root: str | Path) -> Path:
    root = Path(repo_root).resolve()
    if not (root / "entrypoints").exists():
        raise FileNotFoundError(f"repo root does not contain entrypoints/: {root}")
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    return root


def run_quickstart(*, repo_root: str | Path) -> int:
    root = ensure_repo_root_on_sys_path(repo_root)

    try:
        from entrypoints.archive_browse import (
            format_archive_brief,
            read_latest_run_archive,
        )
        from entrypoints.cli import inspect_state_command, load_settings, run_command
    except Exception as exc:  # pragma: no cover - import failure path
        print("Quickstart failed before runtime checks.", file=sys.stderr)
        print(f"repo_root: {root}", file=sys.stderr)
        print(f"import_error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "Tip: run this repository-local script as `python quickstart.py` from the cloned repo.",
            file=sys.stderr,
        )
        return 1

    try:
        settings = load_settings()
        inspect_payload = inspect_state_command(settings)
        run_payload = run_command("ping", settings, task_type="retrieval")
        archive_payload = read_latest_run_archive(settings.artifacts_dir / "runs")
    except Exception as exc:
        print("Quickstart failed during the first-run path.", file=sys.stderr)
        print(f"repo_root: {root}", file=sys.stderr)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("Fallback commands:", file=sys.stderr)
        print("- python -m entrypoints.cli inspect-state", file=sys.stderr)
        print(
            '- python -m entrypoints.cli run --task "ping" --task-type retrieval',
            file=sys.stderr,
        )
        print("- python -m entrypoints.cli archive --latest", file=sys.stderr)
        return 1

    run_archive = (
        run_payload.get("run_archive") if isinstance(run_payload, dict) else {}
    )
    run_id = ""
    if isinstance(run_archive, dict):
        run_id = str(run_archive.get("run_id") or "").strip()

    print("archive-first-harness quickstart")
    print(f"repo_root: {root}")
    print(f"artifacts_dir: {settings.artifacts_dir}")
    print()
    print("[1/3] inspect-state")
    print(
        "status: ok"
        + f" | state_dir={inspect_payload.get('state_dir', '')}"
        + f" | state_file_count={inspect_payload.get('state_file_count', 0)}"
    )
    print()
    print('[2/3] run --task "ping" --task-type retrieval')
    print(
        f"execution_status: {run_payload.get('execution_result', {}).get('status', '')}"
        + f" | verification_passed={bool(run_payload.get('verification_report', {}).get('passed'))}"
        + f" | run_id={run_id or 'unknown'}"
    )
    print(
        "note: raw run JSON is intentionally skipped here; start with the archive summary below."
    )
    print()
    print("[3/3] archive --latest")
    print(format_archive_brief(archive_payload))
    print()
    print("next:")
    print(
        "- compare real runs later with: python -m entrypoints.cli archive --compare-run-id <left> --compare-run-id <right>"
    )
    print("- get deterministic demo runs with: python -m entrypoints.cli demo")
    return 0
