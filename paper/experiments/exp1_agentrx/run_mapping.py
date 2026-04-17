from __future__ import annotations

"""Run the stage-mapping analysis for AgentRx rows.

Outputs:
- summary.json
- stage_counts.json
- category_to_stage_table.md
"""

from collections import Counter, defaultdict
import json
from pathlib import Path

from adapter import AGENTRX_TO_EVIDENCE_STAGE, load_rows, map_row_to_evidence_record


def build_summary(rows: list[dict]) -> dict:
    records = [map_row_to_evidence_record(row) for row in rows]
    total = len(records)
    category_counts = Counter(record["agentrx_root_category"] for record in records)
    stage_counts = Counter(record["mapped_evidence_stage"] for record in records)
    mapping_counts: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        mapping_counts[record["agentrx_root_category"]][
            record["mapped_evidence_stage"]
        ] += 1

    return {
        "total_rows": total,
        "category_counts": dict(sorted(category_counts.items())),
        "stage_counts": dict(sorted(stage_counts.items())),
        "mapping_counts": {
            category: dict(sorted(counter.items()))
            for category, counter in sorted(mapping_counts.items())
        },
        "taxonomy_map": AGENTRX_TO_EVIDENCE_STAGE,
    }


def write_markdown_table(summary: dict, output_path: Path) -> None:
    lines = [
        "# AgentRx → Evidence Layer Mapping",
        "",
        "| AgentRx Root Category | Mapped Evidence Stage | Count |",
        "|---|---:|---:|",
    ]
    for category, mapped_stage in AGENTRX_TO_EVIDENCE_STAGE.items():
        count = int(summary["category_counts"].get(category, 0))
        lines.append(f"| {category} | {mapped_stage} | {count} |")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run AgentRx stage mapping")
    parser.add_argument("input", help="Input AgentRx JSONL file")
    parser.add_argument("--outdir", default="results", help="Output results directory")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(args.input)
    summary = build_summary(rows)

    (outdir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (outdir / "stage_counts.json").write_text(
        json.dumps(summary["stage_counts"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_table(summary, outdir / "category_to_stage_table.md")

    print(
        json.dumps(
            {
                "status": "ok",
                "rows": summary["total_rows"],
                "outdir": str(outdir),
                "stage_counts": summary["stage_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
