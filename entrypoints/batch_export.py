from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from entrypoints._utils import json_dumps, normalize_optional_string


@dataclass(slots=True)
class BatchExportOptions:
    output_dir: str | Path
    base_name: str | None = None
    write_json: bool = True
    write_jsonl: bool = True
    write_markdown_summary: bool = True

    def __post_init__(self) -> None:
        output_dir_text = normalize_optional_string(self.output_dir)
        if not output_dir_text:
            raise ValueError("output_dir must not be empty")
        self.output_dir = Path(output_dir_text)
        self.base_name = normalize_optional_string(self.base_name)
        if not isinstance(self.write_json, bool):
            raise TypeError("write_json must be a boolean")
        if not isinstance(self.write_jsonl, bool):
            raise TypeError("write_jsonl must be a boolean")
        if not isinstance(self.write_markdown_summary, bool):
            raise TypeError("write_markdown_summary must be a boolean")
        if not any((self.write_json, self.write_jsonl, self.write_markdown_summary)):
            raise ValueError("at least one export format must be enabled")


def export_batch_results(
    batch_result: Mapping[str, Any],
    options: BatchExportOptions | Mapping[str, object],
) -> dict[str, Any]:
    if not isinstance(batch_result, Mapping):
        raise TypeError("batch_result must be a mapping")

    export_options = _coerce_batch_export_options(options)
    output_dir = export_options.output_dir.expanduser()
    if not output_dir.is_absolute():
        output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = _resolve_base_name(
        export_options.base_name,
        normalize_optional_string(batch_result.get("batch_name")),
    )
    written_files: list[dict[str, str]] = []
    exported_formats: list[str] = []

    if export_options.write_json:
        json_path = output_dir / f"{base_name}.json"
        json_path.write_text(json_dumps(batch_result), encoding="utf-8")
        written_files.append({"format": "json", "path": str(json_path)})
        exported_formats.append("json")

    if export_options.write_jsonl:
        jsonl_path = output_dir / f"{base_name}.jsonl"
        jsonl_path.write_text(_build_jsonl_payload(batch_result), encoding="utf-8")
        written_files.append({"format": "jsonl", "path": str(jsonl_path)})
        exported_formats.append("jsonl")

    if export_options.write_markdown_summary:
        summary_path = output_dir / f"{base_name}_summary.md"
        summary_path.write_text(_build_markdown_summary(batch_result), encoding="utf-8")
        written_files.append({"format": "markdown", "path": str(summary_path)})
        exported_formats.append("markdown")

    return {
        "output_dir": str(output_dir),
        "base_name": base_name,
        "written_files": written_files,
        "exported_formats": exported_formats,
    }


def _coerce_batch_export_options(
    options: BatchExportOptions | Mapping[str, object],
) -> BatchExportOptions:
    if isinstance(options, BatchExportOptions):
        return options
    if not isinstance(options, Mapping):
        raise TypeError("options must be a BatchExportOptions or mapping")
    return BatchExportOptions(
        output_dir=options.get("output_dir") or "",
        base_name=normalize_optional_string(options.get("base_name")),
        write_json=bool(options.get("write_json", True)),
        write_jsonl=bool(options.get("write_jsonl", True)),
        write_markdown_summary=bool(options.get("write_markdown_summary", True)),
    )


def _build_jsonl_payload(batch_result: Mapping[str, Any]) -> str:
    rows = [
        _build_jsonl_row(item, index)
        for index, item in enumerate(_extract_results(batch_result))
    ]
    if not rows:
        return ""
    return (
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows)
        + "\n"
    )


def _build_jsonl_row(result_item: Mapping[str, Any], index: int) -> dict[str, Any]:
    surface_result = result_item.get("result")
    execution_result = (
        surface_result.get("execution_result")
        if isinstance(surface_result, Mapping)
        else None
    )
    verification_report = (
        surface_result.get("verification_report")
        if isinstance(surface_result, Mapping)
        else None
    )
    error_payload = result_item.get("error")
    return {
        "task_index": result_item.get("task_index", index),
        "task": normalize_optional_string(result_item.get("task")) or f"task-{index}",
        "status": normalize_optional_string(result_item.get("status")) or "unknown",
        "workflow_profile_id": _extract_workflow_profile_id(result_item),
        "execution_status": execution_result.get("status")
        if isinstance(execution_result, Mapping)
        else None,
        "verification_passed": verification_report.get("passed")
        if isinstance(verification_report, Mapping)
        else None,
        "error_type": error_payload.get("type")
        if isinstance(error_payload, Mapping)
        else None,
    }


def _build_markdown_summary(batch_result: Mapping[str, Any]) -> str:
    batch_name = normalize_optional_string(batch_result.get("batch_name")) or "batch"
    total_tasks = int(batch_result.get("total_tasks", 0) or 0)
    completed_tasks = int(batch_result.get("completed_tasks", 0) or 0)
    failed_tasks = int(batch_result.get("failed_tasks", 0) or 0)
    stopped_early = bool(batch_result.get("stopped_early", False))
    lines = [
        f"# Batch Summary: {batch_name}",
        "",
        "- Summary: "
        + (
            normalize_optional_string(batch_result.get("summary"))
            or "No summary recorded."
        ),
        f"- Total tasks: {total_tasks}",
        f"- Completed tasks: {completed_tasks}",
        f"- Failed tasks: {failed_tasks}",
        f"- Stopped early: {'yes' if stopped_early else 'no'}",
        "",
        "## Tasks",
        "",
    ]

    results = _extract_results(batch_result)
    for index, item in enumerate(results):
        task_index = item.get("task_index", index)
        task_text = _truncate_text(
            normalize_optional_string(item.get("task")) or f"task-{task_index}", 120
        )
        status = normalize_optional_string(item.get("status")) or "unknown"
        workflow_profile_id = _extract_workflow_profile_id(item)
        line = f"- [{task_index}] `{status}`"
        if workflow_profile_id:
            line += f" `{workflow_profile_id}`"
        line += f" {task_text}"
        lines.append(line)

    failure_lines = _build_failure_lines(results)
    if failure_lines:
        lines.extend(["", "## Failures", ""])
        lines.extend(failure_lines)

    lines.append("")
    return "\n".join(lines)


def _build_failure_lines(results: Sequence[Mapping[str, Any]]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(results):
        if normalize_optional_string(item.get("status")) != "failed":
            continue
        task_index = item.get("task_index", index)
        task_text = _truncate_text(
            normalize_optional_string(item.get("task")) or f"task-{task_index}", 100
        )
        error_payload = item.get("error")
        if isinstance(error_payload, Mapping):
            error_type = normalize_optional_string(error_payload.get("type")) or "error"
            error_message = _truncate_text(
                normalize_optional_string(error_payload.get("message")) or "", 100
            )
            detail = f"{error_type}: {error_message}".strip(": ")
        else:
            detail = "surface result reported failure"
        lines.append(f"- [{task_index}] {task_text}: {detail}")
    return lines


def _extract_results(batch_result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_results = batch_result.get("results")
    if not isinstance(raw_results, Sequence) or isinstance(
        raw_results, (str, bytes, bytearray)
    ):
        return []
    extracted: list[Mapping[str, Any]] = []
    for item in raw_results:
        if isinstance(item, Mapping):
            extracted.append(item)
    return extracted


def _extract_workflow_profile_id(result_item: Mapping[str, Any]) -> str | None:
    surface_result = result_item.get("result")
    if not isinstance(surface_result, Mapping):
        return None
    surface_payload = surface_result.get("surface")
    if isinstance(surface_payload, Mapping):
        profile_id = normalize_optional_string(
            surface_payload.get("workflow_profile_id")
        )
        if profile_id:
            return profile_id
    evaluation_input_bundle = surface_result.get("evaluation_input_bundle")
    if isinstance(evaluation_input_bundle, Mapping):
        task_contract_summary = evaluation_input_bundle.get("task_contract_summary")
        if isinstance(task_contract_summary, Mapping):
            profile_id = normalize_optional_string(
                task_contract_summary.get("workflow_profile_id")
            )
            if profile_id:
                return profile_id
    return None


def _resolve_base_name(base_name: str | None, batch_name: str | None) -> str:
    for candidate in (base_name, batch_name, "batch_result"):
        normalized = _normalize_base_name(candidate)
        if normalized:
            return normalized
    return "batch_result"


def _normalize_base_name(value: object | None) -> str | None:
    text = normalize_optional_string(value)
    if not text:
        return None
    characters: list[str] = []
    previous_was_separator = False
    for char in text.lower():
        if char.isalnum():
            characters.append(char)
            previous_was_separator = False
            continue
        if char in {"-", "_"}:
            characters.append(char)
            previous_was_separator = False
            continue
        if not previous_was_separator:
            characters.append("_")
            previous_was_separator = True
    normalized = "".join(characters).strip("_-")
    return normalized or None


def _truncate_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."
