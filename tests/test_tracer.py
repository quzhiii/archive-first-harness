from __future__ import annotations

import unittest

from harness.telemetry.metrics import MetricsAggregator
from harness.telemetry.tracer import Tracer


class TracerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tracer = Tracer()
        self.aggregator = MetricsAggregator()

    def test_records_event(self) -> None:
        event = self.tracer.record_event("run_started", {"task_id": "task-1"})

        self.assertEqual(event["event_name"], "run_started")
        self.assertEqual(event["payload"]["task_id"], "task-1")

    def test_records_metric(self) -> None:
        metric = self.tracer.record_metric("latency_ms", 42, tags={"stage": "executor"})

        self.assertEqual(metric["metric_name"], "latency_ms")
        self.assertEqual(metric["value"], 42)
        self.assertEqual(metric["tags"]["stage"], "executor")

    def test_get_trace_returns_structured_trace(self) -> None:
        self.tracer.record_event("run_started", {"task_id": "task-1"})
        self.tracer.record_metric("token_count", 100)

        trace = self.tracer.get_trace()

        self.assertIn("events", trace)
        self.assertIn("metrics", trace)
        self.assertEqual(len(trace["events"]), 1)
        self.assertEqual(len(trace["metrics"]), 1)

    def test_metrics_aggregator_produces_minimal_summary(self) -> None:
        self.tracer.record_event("run_started", {"task_id": "task-1"})
        self.tracer.record_event("run_finished", {"task_id": "task-1"})
        self.tracer.record_metric("latency_ms", 50)
        self.tracer.record_metric("latency_ms", 70)
        self.tracer.record_metric("token_count", 120)

        summary = self.aggregator.aggregate(self.tracer.get_trace())

        self.assertEqual(summary["event_count"], 2)
        self.assertEqual(summary["metric_count"], 3)
        self.assertEqual(summary["events_by_name"]["run_started"], 1)
        self.assertEqual(summary["metrics"]["latency_ms"]["count"], 2)
        self.assertEqual(summary["metrics"]["latency_ms"]["average"], 60.0)

    def test_aggregated_summary_format_is_clear(self) -> None:
        self.tracer.record_metric("rollback_count", 1)
        self.aggregator.aggregate(self.tracer.get_trace())

        exported = self.aggregator.export()

        self.assertIn("event_count", exported)
        self.assertIn("metric_count", exported)
        self.assertIn("metrics", exported)
        self.assertIn("rollback_count", exported["metrics"])


if __name__ == "__main__":
    unittest.main()
