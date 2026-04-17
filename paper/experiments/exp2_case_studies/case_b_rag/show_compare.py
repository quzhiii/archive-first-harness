from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from entrypoints.archive_browse import compare_run_archives, format_archive_brief


ARCHIVE_ROOT = REPO_ROOT / "paper" / "data" / "case_study_archives" / "case_b_rag"


def main() -> None:
    payload = compare_run_archives(
        ARCHIVE_ROOT, "case_b_rag_success", "case_b_rag_failure"
    )
    print(format_archive_brief(payload))


if __name__ == "__main__":
    main()
