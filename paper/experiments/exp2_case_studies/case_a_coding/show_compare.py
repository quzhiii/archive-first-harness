from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from entrypoints.archive_browse import compare_run_archives, format_archive_brief


ARCHIVE_ROOT = REPO_ROOT / "paper" / "data" / "case_study_archives" / "case_a_coding"


def main() -> None:
    parser = argparse.ArgumentParser(description="Show Case A archive comparison.")
    parser.add_argument("--left", default="case_a_coding_success")
    parser.add_argument("--right", default="case_a_coding_failure")
    args = parser.parse_args()

    payload = compare_run_archives(ARCHIVE_ROOT, args.left, args.right)
    print(format_archive_brief(payload))


if __name__ == "__main__":
    main()
