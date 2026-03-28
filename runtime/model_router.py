from __future__ import annotations

from typing import Any


class ModelRouter:
    """Route a task contract to a model slot using simple rule-based heuristics."""

    SLOT_ORDER = ("cheap", "balanced", "strong", "escalated")

    def route(
        self,
        task_contract,
        *,
        current_slot: str | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        selected_slot, reason_codes = self._select_base_slot(task_contract)
        hysteresis_applied = False

        normalized_current = self._normalize_slot(current_slot)
        if normalized_current is not None:
            current_index = self.SLOT_ORDER.index(normalized_current)
            selected_index = self.SLOT_ORDER.index(selected_slot)
            if selected_index < current_index:
                combined_history = list(history or [])
                combined_history.append({"selected_slot": selected_slot})
                if not self.should_deescalate(combined_history):
                    selected_slot = normalized_current
                    hysteresis_applied = True
                    reason_codes.append("deescalation_blocked_by_hysteresis")

        escalation_allowed = self._can_escalate(task_contract, selected_slot)
        return self.build_routing_decision(
            selected_slot=selected_slot,
            reason_codes=reason_codes,
            escalation_allowed=escalation_allowed,
            hysteresis_applied=hysteresis_applied,
            metadata={
                "task_type": getattr(getattr(task_contract, "task_type", None), "value", None),
                "token_budget": getattr(getattr(task_contract, "token_budget", None), "value", None),
                "latency_budget": getattr(getattr(task_contract, "latency_budget", None), "value", None),
                "uncertainty_level": getattr(
                    getattr(task_contract, "uncertainty_level", None), "value", None
                ),
                "residual_risk_level": getattr(
                    getattr(task_contract, "residual_risk_level", None), "value", None
                ),
                "previous_slot": normalized_current,
            },
        )

    def escalate(self, current_slot: str, reason: str) -> dict[str, Any]:
        normalized_current = self._normalize_slot(current_slot)
        if normalized_current is None:
            raise ValueError("current_slot must be one of the supported slots")

        current_index = self.SLOT_ORDER.index(normalized_current)
        next_index = min(current_index + 1, len(self.SLOT_ORDER) - 1)
        next_slot = self.SLOT_ORDER[next_index]
        return self.build_routing_decision(
            selected_slot=next_slot,
            reason_codes=[reason.strip() or "manual_escalation"],
            escalation_allowed=next_slot != self.SLOT_ORDER[-1],
            hysteresis_applied=False,
            metadata={
                "previous_slot": normalized_current,
                "decision_type": "escalate",
            },
        )

    def should_deescalate(self, history: list[dict[str, Any]] | None) -> bool:
        normalized_history = [
            self._normalize_slot(item.get("selected_slot"))
            for item in (history or [])
            if isinstance(item, dict)
        ]
        normalized_history = [slot for slot in normalized_history if slot is not None]
        if len(normalized_history) < 2:
            return False
        return normalized_history[-1] == normalized_history[-2]

    def build_routing_decision(
        self,
        *,
        selected_slot: str,
        reason_codes: list[str],
        escalation_allowed: bool,
        hysteresis_applied: bool,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "selected_slot": selected_slot,
            "reason_codes": list(dict.fromkeys(reason_codes)),
            "escalation_allowed": escalation_allowed,
            "hysteresis_applied": hysteresis_applied,
            "metadata": dict(metadata),
        }

    def _select_base_slot(self, task_contract) -> tuple[str, list[str]]:
        selected_index = 0
        reason_codes: list[str] = []

        task_type = getattr(getattr(task_contract, "task_type", None), "value", "")
        token_budget = getattr(getattr(task_contract, "token_budget", None), "value", "")
        latency_budget = getattr(getattr(task_contract, "latency_budget", None), "value", "")
        uncertainty_level = getattr(getattr(task_contract, "uncertainty_level", None), "value", "")
        residual_risk_level = getattr(
            getattr(task_contract, "residual_risk_level", None), "value", ""
        )

        if task_type in {"coding", "research", "review", "qa", "planning"}:
            selected_index = max(selected_index, 1)
            reason_codes.append("task_type_requires_balanced_slot")
        elif task_type in {"retrieval", "generation", "execution"}:
            reason_codes.append("task_type_allows_low_cost_slot")

        if token_budget == "medium" and selected_index == 0 and task_type in {
            "planning",
            "research",
            "coding",
            "review",
            "qa",
        }:
            selected_index = max(selected_index, 1)
            reason_codes.append("medium_token_budget")
        elif token_budget == "high":
            selected_index = max(selected_index, 2)
            reason_codes.append("high_token_budget")

        if latency_budget == "high" and selected_index < 2 and task_type in {
            "coding",
            "research",
            "review",
            "qa",
        }:
            selected_index = max(selected_index, 1)
            reason_codes.append("high_latency_budget")
        elif latency_budget == "low":
            reason_codes.append("latency_constrained")

        if uncertainty_level == "high":
            selected_index = min(selected_index + 1, len(self.SLOT_ORDER) - 1)
            reason_codes.append("high_uncertainty")
        if residual_risk_level == "high":
            selected_index = min(selected_index + 1, len(self.SLOT_ORDER) - 1)
            reason_codes.append("high_residual_risk")

        if not reason_codes:
            reason_codes.append("default_route")

        return self.SLOT_ORDER[selected_index], reason_codes

    def _can_escalate(self, task_contract, selected_slot: str) -> bool:
        if selected_slot == self.SLOT_ORDER[-1]:
            return False
        uncertainty_level = getattr(getattr(task_contract, "uncertainty_level", None), "value", "")
        residual_risk_level = getattr(
            getattr(task_contract, "residual_risk_level", None), "value", ""
        )
        return uncertainty_level == "high" or residual_risk_level == "high"

    def _normalize_slot(self, slot: str | None) -> str | None:
        if slot is None:
            return None
        normalized = slot.strip().lower()
        if normalized not in self.SLOT_ORDER:
            return None
        return normalized
