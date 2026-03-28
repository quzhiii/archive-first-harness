from __future__ import annotations

from typing import Any


class RealmEvaluator:
    """Convert a minimal metrics summary into a conservative recommendation."""

    def evaluate(self, metrics_summary: dict[str, Any]) -> dict[str, Any]:
        recommendation, reason_codes = self.build_recommendation(metrics_summary)
        summary = self.explain_decision(recommendation, reason_codes)
        return {
            "status": "ok",
            "recommendation": recommendation,
            "reason_codes": reason_codes,
            "summary": summary,
            "requires_human_review": recommendation != "keep",
            "metadata": {
                "automatic_action": "none",
                "source": "v0.1 rule-based realm evaluator",
                "metric_count": len(metrics_summary.get("metrics", {})),
            },
        }

    def build_recommendation(self, metrics_summary: dict[str, Any]) -> tuple[str, list[str]]:
        reason_codes: list[str] = []

        retry_count = self._metric_last(metrics_summary, "retry_count")
        rollback_count = self._metric_last(metrics_summary, "rollback_count")
        human_handoff_count = self._metric_last(metrics_summary, "human_handoff_count")
        latency_ms = self._metric_last(metrics_summary, "latency_ms")
        context_size = self._metric_last(metrics_summary, "context_size")
        skill_hit_rate = self._metric_last(metrics_summary, "skill_hit_rate")
        token_count = self._metric_last(metrics_summary, "token_count")
        execution_failure_count = self._metric_last(metrics_summary, "execution_failure_count")

        if retry_count >= 3:
            reason_codes.append("high_retry_count")
        elif retry_count > 0:
            reason_codes.append("retry_activity_detected")

        if rollback_count >= 2:
            reason_codes.append("high_rollback_count")
        elif rollback_count > 0:
            reason_codes.append("rollback_activity_detected")

        if human_handoff_count > 0:
            reason_codes.append("human_handoff_detected")
        if latency_ms >= 5000:
            reason_codes.append("high_latency")
        elif latency_ms >= 2000:
            reason_codes.append("moderate_latency")
        if context_size >= 100:
            reason_codes.append("oversized_context")
        elif context_size >= 40:
            reason_codes.append("growing_context")
        if token_count >= 5000:
            reason_codes.append("high_token_cost")
        elif token_count >= 1500:
            reason_codes.append("moderate_token_cost")
        if execution_failure_count > 0:
            reason_codes.append("execution_failure_detected")
        if self._has_metric(metrics_summary, "skill_hit_rate") and skill_hit_rate == 0:
            reason_codes.append("no_skill_hits")

        strong_signals = {
            "execution_failure_detected",
            "high_retry_count",
            "high_rollback_count",
            "human_handoff_detected",
            "high_latency",
            "oversized_context",
        }
        strong_count = sum(1 for code in reason_codes if code in strong_signals)

        if strong_count >= 2 and "no_skill_hits" in reason_codes:
            return "retire_candidate", reason_codes
        if strong_count >= 2:
            return "observe", reason_codes
        if reason_codes:
            return "observe", reason_codes
        return "keep", ["stable_baseline"]

    def explain_decision(self, recommendation: str, reason_codes: list[str]) -> str:
        if recommendation == "keep":
            return "Current signals are stable enough to keep the component in the v0.1 path."
        if recommendation == "observe":
            joined = ", ".join(reason_codes)
            return f"Observed non-critical pressure signals: {joined}. Keep the component, but review it later."
        joined = ", ".join(reason_codes)
        return (
            f"The component is a retire candidate because repeated overhead signals were detected: {joined}. "
            "This is advisory only and requires human review."
        )

    def _metric_last(self, metrics_summary: dict[str, Any], metric_name: str) -> float:
        metric = metrics_summary.get("metrics", {}).get(metric_name, {})
        try:
            return float(metric.get("last", 0))
        except (TypeError, ValueError):
            return 0.0

    def _has_metric(self, metrics_summary: dict[str, Any], metric_name: str) -> bool:
        return metric_name in metrics_summary.get("metrics", {})
