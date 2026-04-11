from __future__ import annotations

from pathlib import Path

from entrypoints.quickstart_flow import run_quickstart


if __name__ == "__main__":
    raise SystemExit(run_quickstart(repo_root=Path(__file__).resolve().parent))
