from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class Tracer:
    """Keep a local structured trace for the current run."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._metrics: list[dict[str, Any]] = []

    def record_event(self, event_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_name": event_name,
            "payload": dict(payload),
        }
        self._events.append(event)
        return event

    def record_metric(
        self,
        metric_name: str,
        value: int | float,
        tags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metric = {
            "timestamp": datetime.now(UTC).isoformat(),
            "metric_name": metric_name,
            "value": value,
            "tags": dict(tags or {}),
        }
        self._metrics.append(metric)
        return metric

    def get_trace(self) -> dict[str, Any]:
        return {
            "events": list(self._events),
            "metrics": list(self._metrics),
        }

    def flush(self) -> dict[str, Any]:
        trace = self.get_trace()
        self._events.clear()
        self._metrics.clear()
        return trace
