from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from entrypoints.settings import Settings
from entrypoints.task_runner import SurfaceTaskRequest, run_task_request, surface_result_succeeded


@dataclass(slots=True)
class SurfaceBatchRequest:
    tasks: list[SurfaceTaskRequest | Mapping[str, object]] = field(default_factory=list)
    batch_name: str | None = None
    stop_on_error: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.tasks = list(self.tasks or [])
        self.batch_name = _normalize_optional_string(self.batch_name)
        self.metadata = dict(self.metadata or {})
        if not isinstance(self.stop_on_error, bool):
            raise TypeError("stop_on_error must be a boolean")
        if not self.tasks:
            raise ValueError("tasks must not be empty")



def run_batch_request(
    request: SurfaceBatchRequest | Mapping[str, object],
    settings: Settings,
    *,
    task_runner=None,
) -> dict[str, Any]:
    batch_request = _coerce_surface_batch_request(request)
    active_task_runner = task_runner or run_task_request
    batch_name = batch_request.batch_name or "batch"
    results: list[dict[str, Any]] = []
    completed_tasks = 0
    failed_tasks = 0
    stopped_early = False

    for index, task_request in enumerate(batch_request.tasks):
        task_label = _extract_task_label(task_request, index)
        try:
            surface_result = active_task_runner(task_request, settings)
            task_failed = not surface_result_succeeded(surface_result)
            results.append(
                {
                    "task_index": index,
                    "task": task_label,
                    "status": "failed" if task_failed else "completed",
                    "result": surface_result,
                }
            )
            if task_failed:
                failed_tasks += 1
            else:
                completed_tasks += 1
        except Exception as exc:
            failed_tasks += 1
            results.append(
                {
                    "task_index": index,
                    "task": task_label,
                    "status": "failed",
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                }
            )

        if results[-1]["status"] == "failed" and batch_request.stop_on_error:
            stopped_early = index < len(batch_request.tasks) - 1
            break

    return {
        "batch_name": batch_name,
        "total_tasks": len(batch_request.tasks),
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "stopped_early": stopped_early,
        "results": results,
        "summary": _build_batch_summary(
            batch_name=batch_name,
            total_tasks=len(batch_request.tasks),
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            stopped_early=stopped_early,
        ),
    }



def load_batch_request_file(
    path: str | Path,
    *,
    batch_name: str | None = None,
    stop_on_error: bool | None = None,
) -> SurfaceBatchRequest:
    batch_path = Path(path)
    suffix = batch_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(batch_path.read_text(encoding="utf-8"))
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            return SurfaceBatchRequest(
                tasks=list(payload),
                batch_name=batch_name or batch_path.stem,
                stop_on_error=bool(stop_on_error) if stop_on_error is not None else False,
            )
        if not isinstance(payload, Mapping):
            raise TypeError("batch json must be a list of tasks or a mapping with tasks")
        tasks = payload.get("tasks")
        if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes, bytearray)):
            raise TypeError("batch json mapping must contain a tasks sequence")
        raw_stop_on_error = payload.get("stop_on_error") if stop_on_error is None else stop_on_error
        raw_metadata = payload.get("metadata")
        metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
        return SurfaceBatchRequest(
            tasks=list(tasks),
            batch_name=batch_name or _normalize_optional_string(payload.get("batch_name")) or batch_path.stem,
            stop_on_error=bool(raw_stop_on_error),
            metadata=metadata,
        )
    if suffix == ".jsonl":
        tasks: list[dict[str, Any]] = []
        for line in batch_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, Mapping):
                raise TypeError("each jsonl line must decode to a task mapping")
            tasks.append(dict(payload))
        return SurfaceBatchRequest(
            tasks=tasks,
            batch_name=batch_name or batch_path.stem,
            stop_on_error=bool(stop_on_error) if stop_on_error is not None else False,
        )
    raise ValueError("batch file must use .json or .jsonl")



def _coerce_surface_batch_request(
    request: SurfaceBatchRequest | Mapping[str, object],
) -> SurfaceBatchRequest:
    if isinstance(request, SurfaceBatchRequest):
        return request
    if not isinstance(request, Mapping):
        raise TypeError("request must be a SurfaceBatchRequest or mapping")

    tasks = request.get("tasks")
    if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes, bytearray)):
        raise TypeError("request.tasks must be a sequence")
    raw_metadata = request.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    return SurfaceBatchRequest(
        tasks=list(tasks),
        batch_name=_normalize_optional_string(request.get("batch_name")),
        stop_on_error=bool(request.get("stop_on_error", False)),
        metadata=metadata,
    )



def _extract_task_label(task_request: SurfaceTaskRequest | Mapping[str, object], index: int) -> str:
    if isinstance(task_request, SurfaceTaskRequest):
        return task_request.task
    if isinstance(task_request, Mapping):
        task_value = task_request.get("task")
        text = _normalize_optional_string(task_value)
        if text:
            return text
    return f"task-{index}"



def _build_batch_summary(
    *,
    batch_name: str,
    total_tasks: int,
    completed_tasks: int,
    failed_tasks: int,
    stopped_early: bool,
) -> str:
    summary = (
        f"Batch '{batch_name}' processed {completed_tasks + failed_tasks}/{total_tasks} tasks; "
        f"{completed_tasks} completed, {failed_tasks} failed."
    )
    if stopped_early:
        return summary + " Stopped early after the first failure."
    return summary



def _normalize_optional_string(value: object | None) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None
