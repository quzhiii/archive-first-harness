from __future__ import annotations

"""Convert AgentRx benchmark rows into archive-first-harness style records.

This adapter does NOT require the full AgentRx raw trajectory payload to be useful.
It can already transform the public dataset metadata row shape into:
1. a normalized internal record for analysis
2. a synthetic archive payload compatible with write_run_archive()

Why synthetic?
- The public dataset card exposes annotations (failures/root_cause), but the raw
  trajectory files are gated behind HF access approval.
- For the paper plan, we can still build the mapping/evaluation pipeline now and
  swap in richer trace details later once the dataset is approved/downloaded.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


AGENTRX_TO_EVIDENCE_STAGE = {
    "Instruction/Plan Adherence Failure": "routing",
    "Instruction Adherence Failure": "routing",
    "Intent-Plan Misalignment": "routing",
    "Intent Plan Misalignment": "routing",
    "Underspecified User Intent": "routing",
    "Intent Not Supported": "routing",
    "Intent not supported": "routing",
    "Invalid Invocation": "execution",
    "Misinterpretation of Tool Output": "execution",
    "Invention of New Information": "execution",
    "Invention of new information": "execution",
    "System Failure": "execution",
    "Guardrails Triggered": "governance",
    "Inconclusive": "unknown",
}

CANONICAL_CATEGORY_NAMES = {
    "Instruction Adherence Failure": "Instruction/Plan Adherence Failure",
    "Instruction/Plan Adherence Failure": "Instruction/Plan Adherence Failure",
    "Intent Plan Misalignment": "Intent-Plan Misalignment",
    "Intent-Plan Misalignment": "Intent-Plan Misalignment",
    "Underspecified User Intent": "Underspecified User Intent",
    "Intent Not Supported": "Intent Not Supported",
    "Intent not supported": "Intent Not Supported",
    "Invalid Invocation": "Invalid Invocation",
    "Misinterpretation of Tool Output": "Misinterpretation of Tool Output",
    "Invention of new information": "Invention of New Information",
    "Invention of New Information": "Invention of New Information",
    "System Failure": "System Failure",
    "Guardrails Triggered": "Guardrails Triggered",
    "Inconclusive": "Inconclusive",
}


@dataclass(slots=True)
class AgentRxFailure:
    failure_id: str
    step_number: int
    step_reason: str
    failure_category: str
    category_reason: str
    failed_agent: str


def load_rows(jsonl_path: str | Path) -> list[dict[str, Any]]:
    path = Path(jsonl_path)
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def extract_root_category(row: dict[str, Any]) -> str:
    root_cause_id = str(row.get("root_cause_failure_id") or "").strip()
    failures = row.get("failures")
    if isinstance(failures, list):
        for failure in failures:
            if not isinstance(failure, dict):
                continue
            if str(failure.get("failure_id") or "").strip() == root_cause_id:
                raw_category = str(failure.get("failure_category") or "").strip()
                return normalize_category_name(raw_category)
    return "Inconclusive"


def normalize_category_name(category: str) -> str:
    return CANONICAL_CATEGORY_NAMES.get(
        category.strip(), category.strip() or "Inconclusive"
    )


def map_row_to_evidence_record(row: dict[str, Any]) -> dict[str, Any]:
    root_category = extract_root_category(row)
    mapped_stage = AGENTRX_TO_EVIDENCE_STAGE.get(root_category, "unknown")
    raw_failures = row.get("failures")
    failures: list[dict[str, Any]] = []
    if isinstance(raw_failures, list):
        failures = [item for item in raw_failures if isinstance(item, dict)]
    failed_agents = sorted(
        {
            str(item.get("failed_agent") or "").strip()
            for item in failures
            if isinstance(item, dict) and str(item.get("failed_agent") or "").strip()
        }
    )
    return {
        "trajectory_id": str(row.get("trajectory_id") or "").strip(),
        "failure_summary": str(row.get("failure_summary") or "").strip(),
        "num_failures": int(row.get("num_failures") or 0),
        "root_cause_failure_id": str(row.get("root_cause_failure_id") or "").strip(),
        "root_cause_reason": str(row.get("root_cause_reason") or "").strip(),
        "agentrx_root_category": root_category,
        "mapped_evidence_stage": mapped_stage,
        "failed_agents": failed_agents,
        "domain_guess": infer_domain(row),
    }


def infer_domain(row: dict[str, Any]) -> str:
    trajectory_id = str(row.get("trajectory_id") or "").lower()
    if "tau" in trajectory_id:
        return "tau_retail"
    if "magentic" in trajectory_id:
        return "magentic_one"
    return "unknown"


def map_row_to_synthetic_run_result(row: dict[str, Any]) -> dict[str, Any]:
    record = map_row_to_evidence_record(row)
    root_category = record["agentrx_root_category"]
    stage = record["mapped_evidence_stage"]
    verification_failed = stage == "verification"
    governance_failed = stage == "governance"
    execution_failed = stage == "execution"

    execution_status = "error" if execution_failed else "success"
    verification_passed = (
        not verification_failed and not execution_failed and not governance_failed
    )

    return {
        "surface": {"workflow_profile_id": "paper_agentrx_mapping"},
        "task_contract": {
            "goal": row.get("failure_summary")
            or "Map AgentRx trajectory into evidence-layer taxonomy.",
            "task_type": "analysis",
            "task_id": record["trajectory_id"],
            "contract_id": f"contract_{record['trajectory_id']}",
            "workflow_profile_id": "paper_agentrx_mapping",
            "success_criteria": [
                "Classify the failed trajectory into an evidence-layer stage.",
            ],
            "expected_artifacts": ["failure_report"],
        },
        "execution_result": {
            "status": execution_status,
            "tool_name": "agentrx_adapter",
            "output": None if execution_failed else record["failure_summary"],
            "error": {
                "type": root_category,
                "message": record["root_cause_reason"] or record["failure_summary"],
            }
            if execution_failed
            else None,
            "artifacts": []
            if execution_failed
            else [
                {
                    "type": "failure_report",
                    "path": f"agentrx/{record['trajectory_id']}.json",
                }
            ],
            "metadata": {
                "paper_experiment": "exp1_agentrx",
                "trajectory_id": record["trajectory_id"],
                "agentrx_root_category": root_category,
                "mapped_evidence_stage": stage,
                "failed_agents": record["failed_agents"],
                "domain": record["domain_guess"],
            },
        },
        "verification_report": {
            "passed": verification_passed,
            "status": "passed" if verification_passed else "failed",
            "warnings": [
                {
                    "code": "agentrx_failed_mapping",
                    "message": record["failure_summary"],
                }
            ]
            if not verification_passed
            else [],
        },
        "metrics_summary": {
            "paper_experiment": "exp1_agentrx",
            "num_failures": record["num_failures"],
            "failed_agent_count": len(record["failed_agents"]),
        },
        "evaluation_input_bundle": {
            "task_contract_summary": {
                "workflow_profile_id": "paper_agentrx_mapping",
                "task_type": "analysis",
            }
        },
        "realm_evaluation": {
            "status": "pass" if verification_passed else "fail",
            "recommendation": "keep" if verification_passed else "observe",
            "requires_human_review": root_category == "Inconclusive",
            "reason_codes": [
                f"agentrx_category:{root_category}",
                f"evidence_stage:{stage}",
            ],
            "metadata": {"automatic_action": "none", "paper_experiment": True},
        },
        "baseline_compare_results": {
            "status": "not_requested",
            "artifact_types": [],
            "status_counts": {},
        },
        "residual_followup": {
            "auto_execution": "none",
            "reassessment": {
                "reassessed_level": "high" if not verification_passed else "low",
                "needs_followup": not verification_passed,
                "reason_codes": [
                    f"agentrx_root_category:{root_category}",
                    f"mapped_stage:{stage}",
                ],
            },
            "governance": {
                "status": "review_required" if governance_failed else "clear",
                "requires_governance_override": governance_failed,
            },
        },
        "trace_events": build_synthetic_trace_events(row, record),
    }


def build_synthetic_trace_events(
    row: dict[str, Any], record: dict[str, Any]
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    raw_failures = row.get("failures")
    failures: list[dict[str, Any]] = []
    if isinstance(raw_failures, list):
        failures = [item for item in raw_failures if isinstance(item, dict)]
    for failure in failures:
        events.append(
            {
                "event_type": "agentrx_failure_annotation",
                "status": "failed",
                "step_number": failure.get("step_number"),
                "metadata": {
                    "failure_id": failure.get("failure_id"),
                    "failure_category": failure.get("failure_category"),
                    "failed_agent": failure.get("failed_agent"),
                    "category_reason": failure.get("category_reason"),
                },
            }
        )
    events.append(
        {
            "event_type": "agentrx_root_cause_selected",
            "status": "failed",
            "metadata": {
                "root_cause_failure_id": record["root_cause_failure_id"],
                "agentrx_root_category": record["agentrx_root_category"],
                "mapped_evidence_stage": record["mapped_evidence_stage"],
            },
        }
    )
    return events


def write_normalized_records(
    rows: list[dict[str, Any]], output_path: str | Path
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(map_row_to_evidence_record(row), ensure_ascii=False) + "\n"
            )
    return out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Normalize AgentRx rows into evidence-layer records"
    )
    parser.add_argument("input", help="Input AgentRx JSONL file")
    parser.add_argument(
        "--output", default="normalized_records.jsonl", help="Output JSONL path"
    )
    args = parser.parse_args()

    rows = load_rows(args.input)
    written = write_normalized_records(rows, args.output)
    print(f"Wrote {len(rows)} normalized rows -> {written}")
