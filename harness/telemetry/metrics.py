from __future__ import annotations

from typing import Any


class MetricsAggregator:
    """Aggregate simple local metrics into a compact summary."""

    def __init__(self) -> None:
        self._summary: dict[str, Any] = {
            "event_count": 0,
            "metric_count": 0,
            "events_by_name": {},
            "metrics": {},
        }

    def aggregate(self, trace: dict[str, Any]) -> dict[str, Any]:
        events = list(trace.get("events", []))
        metrics = list(trace.get("metrics", []))

        events_by_name: dict[str, int] = {}
        for event in events:
            name = str(event.get("event_name") or "unknown")
            events_by_name[name] = events_by_name.get(name, 0) + 1

        metrics_summary: dict[str, dict[str, Any]] = {}
        for metric in metrics:
            name = str(metric.get("metric_name") or "unknown")
            value = float(metric.get("value", 0))
            current = metrics_summary.setdefault(
                name,
                {
                    "count": 0,
                    "sum": 0.0,
                    "min": value,
                    "max": value,
                    "last": value,
                    "average": 0.0,
                },
            )
            current["count"] += 1
            current["sum"] += value
            current["min"] = min(current["min"], value)
            current["max"] = max(current["max"], value)
            current["last"] = value
            current["average"] = current["sum"] / current["count"]

        self._summary = {
            "event_count": len(events),
            "metric_count": len(metrics),
            "events_by_name": events_by_name,
            "metrics": metrics_summary,
        }
        return self._summary

    def summarize(self) -> dict[str, Any]:
        return dict(self._summary)

    def export(self) -> dict[str, Any]:
        return self.summarize()
