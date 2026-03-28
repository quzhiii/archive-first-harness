from __future__ import annotations

from typing import Any


class MethodologyRouter:
    """Select a methodology inside the task contract boundary when possible."""

    SUPPORTED_METHODOLOGIES = (
        "debug",
        "build",
        "research",
        "architecture",
        "performance",
    )

    TASK_TYPE_DEFAULTS = {
        "coding": "build",
        "execution": "build",
        "generation": "build",
        "research": "research",
        "retrieval": "research",
        "planning": "architecture",
        "review": "debug",
        "qa": "debug",
    }

    FAMILY_BOUNDARIES = {
        "build": {"build", "debug", "performance"},
        "debug": {"debug", "build", "performance"},
        "research": {"research", "architecture"},
        "architecture": {"architecture", "research"},
        "performance": {"performance", "debug", "build"},
    }

    def route(
        self,
        task_contract,
        *,
        failure_tier: str | None = None,
        tool_outcome: str | None = None,
        evidence_quality: str | None = None,
        context_health: str | None = None,
        budget_remaining: str | None = None,
    ) -> dict[str, Any]:
        contract_methodology = self._resolve_contract_methodology(task_contract)
        normalized_signals = {
            "failure_tier": self._normalize_signal(failure_tier, "none"),
            "tool_outcome": self._normalize_signal(tool_outcome, "success"),
            "evidence_quality": self._normalize_signal(evidence_quality, "adequate"),
            "context_health": self._normalize_signal(context_health, "healthy"),
            "budget_remaining": self._normalize_signal(budget_remaining, "medium"),
        }

        allowed_methodologies = self._allowed_methodologies(task_contract, contract_methodology)
        candidate, selection_reason = self._match_contract_failure_policy(
            task_contract,
            normalized_signals,
        )
        if candidate is None:
            candidate, selection_reason = self._select_fallback_methodology(
                contract_methodology,
                normalized_signals,
            )

        is_within_contract = candidate in allowed_methodologies
        requires_governance_override = not is_within_contract
        expected_next_action = self._build_expected_next_action(
            candidate,
            contract_methodology,
            is_within_contract,
            selection_reason,
        )

        return self.build_routing_decision(
            selected_methodology=candidate,
            selection_reason=selection_reason,
            is_within_contract=is_within_contract,
            requires_governance_override=requires_governance_override,
            expected_next_action=expected_next_action,
        )

    def build_routing_decision(
        self,
        *,
        selected_methodology: str,
        selection_reason: str,
        is_within_contract: bool,
        requires_governance_override: bool,
        expected_next_action: str,
    ) -> dict[str, Any]:
        return {
            "selected_methodology": selected_methodology,
            "selection_reason": selection_reason,
            "is_within_contract": is_within_contract,
            "requires_governance_override": requires_governance_override,
            "expected_next_action": expected_next_action,
        }

    def _resolve_contract_methodology(self, task_contract) -> str:
        family = self._normalize_signal(getattr(task_contract, "methodology_family", None), "")
        if family in self.SUPPORTED_METHODOLOGIES:
            return family

        task_type = self._normalize_signal(
            getattr(getattr(task_contract, "task_type", None), "value", None),
            "generation",
        )
        return self.TASK_TYPE_DEFAULTS.get(task_type, "build")

    def _allowed_methodologies(self, task_contract, contract_methodology: str) -> set[str]:
        allowed = set(self.FAMILY_BOUNDARIES.get(contract_methodology, {contract_methodology}))
        for policy in getattr(task_contract, "failure_escalation_policy", []):
            parsed = self._parse_failure_policy(policy)
            if parsed is not None:
                allowed.add(parsed[2])
        return allowed

    def _match_contract_failure_policy(
        self,
        task_contract,
        normalized_signals: dict[str, str],
    ) -> tuple[str | None, str]:
        for policy in getattr(task_contract, "failure_escalation_policy", []):
            parsed = self._parse_failure_policy(policy)
            if parsed is None:
                continue
            signal_name, expected_value, methodology = parsed
            if normalized_signals.get(signal_name) == expected_value:
                return methodology, f"contract_failure_policy:{signal_name}:{expected_value}"
        return None, ""

    def _select_fallback_methodology(
        self,
        contract_methodology: str,
        normalized_signals: dict[str, str],
    ) -> tuple[str, str]:
        failure_tier = normalized_signals["failure_tier"]
        tool_outcome = normalized_signals["tool_outcome"]
        evidence_quality = normalized_signals["evidence_quality"]
        context_health = normalized_signals["context_health"]
        budget_remaining = normalized_signals["budget_remaining"]

        if failure_tier in {"performance", "latency"} or tool_outcome == "slow":
            return "performance", "fallback_performance_for_runtime_signal"
        if failure_tier in {
            "tool_failure",
            "runtime_error",
            "assertion_failure",
            "execution_error",
        } or tool_outcome in {"error", "failed", "timeout"}:
            return "debug", "fallback_debug_for_failure_signal"
        if evidence_quality in {"low", "weak", "missing"}:
            return "research", "fallback_research_for_low_evidence"
        if context_health in {"poor", "stale", "bloated"}:
            return "architecture", "fallback_architecture_for_context_health"
        if budget_remaining in {"low", "critical", "exhausted"}:
            return contract_methodology, "contract_default_due_to_budget_guardrail"
        return contract_methodology, "contract_default_methodology"

    def _build_expected_next_action(
        self,
        candidate: str,
        contract_methodology: str,
        is_within_contract: bool,
        selection_reason: str,
    ) -> str:
        if not is_within_contract:
            return f"request_governance_override_for_{candidate}"
        if selection_reason.startswith("contract_failure_policy:"):
            return f"apply_contract_policy_with_{candidate}"
        if candidate == contract_methodology:
            return f"continue_with_{candidate}"
        return f"switch_to_{candidate}"

    def _parse_failure_policy(self, policy: object) -> tuple[str, str, str] | None:
        text = str(policy or "").strip().lower()
        if not text or "=>" not in text or ":" not in text:
            return None

        left, right = text.split("=>", 1)
        signal_name, expected_value = left.split(":", 1)
        methodology = right.strip()
        signal_name = signal_name.strip()
        expected_value = expected_value.strip()
        if methodology not in self.SUPPORTED_METHODOLOGIES:
            return None
        if signal_name not in {
            "failure_tier",
            "tool_outcome",
            "evidence_quality",
            "context_health",
            "budget_remaining",
        }:
            return None
        if not expected_value:
            return None
        return signal_name, expected_value, methodology

    def _normalize_signal(self, value: object, default: str) -> str:
        text = str(value or "").strip().lower()
        return text or default
