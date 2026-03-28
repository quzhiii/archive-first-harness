from __future__ import annotations

from typing import Any


class GovernancePolicy:
    """Apply minimal governance checks to advisory follow-up decisions."""

    def review_execution_gate(
        self,
        *,
        task_contract,
        action: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        action = dict(action or {})
        tool_name = str(action.get("tool_name") or "").strip()
        risk_level = self._normalize_enum(getattr(task_contract, "residual_risk_level", "low"))
        write_permission_level = self._normalize_enum(
            getattr(task_contract, "write_permission_level", "read")
        )

        issues: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        high_permission = write_permission_level in {"write", "destructive_write"}
        high_risk = risk_level == "high"
        governance_required = False

        if high_permission:
            reason_codes.append("high_write_permission")
        if high_risk:
            reason_codes.append("high_risk_level")

        if write_permission_level == "destructive_write":
            governance_required = True
            reason_codes.append("governance_requires_isolation")
            issues.append(
                {
                    "code": "destructive_write_requires_isolation",
                    "message": "destructive writes require isolated execution",
                    "action": tool_name or "unspecified_action",
                }
            )
        elif tool_name == "run_command" and high_permission:
            governance_required = True
            reason_codes.append("governance_requires_isolation")
            issues.append(
                {
                    "code": "command_write_requires_isolation",
                    "message": "write-capable command execution requires isolated execution",
                    "action": tool_name,
                }
            )

        requires_sandbox = high_permission or high_risk or governance_required
        return {
            "status": "sandbox_required" if requires_sandbox else "direct_execution_allowed",
            "sandbox_required": requires_sandbox,
            "governance_required": governance_required,
            "reason_codes": reason_codes,
            "issues": issues,
            "risk_level": risk_level,
            "write_permission_level": write_permission_level,
            "action": tool_name or None,
        }

    def review_followup(
        self,
        *,
        task_contract,
        methodology_decision: dict[str, Any] | None = None,
        model_decision: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        if methodology_decision and methodology_decision.get("requires_governance_override"):
            issues.append(
                {
                    "code": "methodology_out_of_contract",
                    "message": (
                        "methodology suggestion exceeds the contract boundary and requires governance review"
                    ),
                    "candidate": methodology_decision.get("selected_methodology"),
                    "contract_methodology": getattr(task_contract, "methodology_family", None),
                }
            )

        if model_decision and model_decision.get("requires_governance_override"):
            issues.append(
                {
                    "code": "model_override_required",
                    "message": "model suggestion requires governance review",
                    "candidate": model_decision.get("selected_slot"),
                }
            )

        requires_override = bool(issues)
        return {
            "status": "review_required" if requires_override else "clear",
            "approved": not requires_override,
            "requires_governance_override": requires_override,
            "issues": issues,
        }

    def _normalize_enum(self, value: Any) -> str:
        raw_value = getattr(value, "value", value)
        return str(raw_value).strip().lower()
