from __future__ import annotations

from copy import deepcopy
from typing import Any


class Verifier:
    """Perform structural verification and residual risk reassessment."""

    REQUIRED_FIELDS = (
        "status",
        "tool_name",
        "output",
        "error",
        "artifacts",
        "metadata",
    )

    def verify_execution_result(
        self,
        execution_result: dict[str, Any],
        task_contract,
    ) -> dict[str, Any]:
        result_copy = deepcopy(execution_result)
        issues = self.check_output_shape(result_copy)
        consistency = self.check_basic_consistency(result_copy, task_contract)
        issues.extend(consistency["issues"])
        warnings = consistency["warnings"]
        passed = len(issues) == 0

        return self.build_verification_report(
            passed=passed,
            issues=issues,
            warnings=warnings,
            execution_result=result_copy,
            task_contract=task_contract,
        )

    def reassess_residual_risk(
        self,
        execution_result: dict[str, Any],
        task_contract,
        verification_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        report = verification_report or self.verify_execution_result(execution_result, task_contract)
        previous_level = self._normalize_risk_level(
            getattr(getattr(task_contract, "residual_risk_level", None), "value", None)
        )
        reassessed_index = self._risk_level_to_index(previous_level)
        reason_codes: list[str] = []
        failure_tier = "none"
        tool_outcome = "success"
        evidence_quality = "adequate"
        context_health = "healthy"
        budget_remaining = "medium"

        issues = list(report.get("issues", []))
        warnings = list(report.get("warnings", []))
        execution_status = str(execution_result.get("status") or "").strip().lower()

        if execution_status == "error":
            reassessed_index = max(reassessed_index, 2)
            reason_codes.append("execution_failed")
            failure_tier = str(
                execution_result.get("error", {}).get("type") or "execution_error"
            ).strip().lower()
            tool_outcome = "error"
            evidence_quality = "low"
            context_health = "degraded"
            budget_remaining = "low"

        if issues:
            reassessed_index = max(reassessed_index, 2)
            reason_codes.append("verification_issues_present")
            if failure_tier == "none":
                failure_tier = "verification_issue"
            if tool_outcome == "success":
                tool_outcome = "error"
            evidence_quality = "low"
            if context_health == "healthy":
                context_health = "fragile"
            budget_remaining = "low"
        elif warnings:
            reassessed_index = max(reassessed_index, 1)
            reason_codes.append("verification_warnings_present")
            if failure_tier == "none":
                failure_tier = "warning_signal"
            if tool_outcome == "success":
                tool_outcome = "partial"
            evidence_quality = "mixed"
            if context_health == "healthy":
                context_health = "watch"
            budget_remaining = "medium"

        if not reason_codes:
            reason_codes.append("execution_clean")

        reassessed_level = self._risk_index_to_level(reassessed_index)
        changed = reassessed_level != previous_level
        return {
            "status": "ok",
            "previous_level": previous_level,
            "reassessed_level": reassessed_level,
            "changed": changed,
            "needs_followup": reassessed_level == "high",
            "reason_codes": list(dict.fromkeys(reason_codes)),
            "failure_tier": failure_tier,
            "tool_outcome": tool_outcome,
            "evidence_quality": evidence_quality,
            "context_health": context_health,
            "budget_remaining": budget_remaining,
            "metadata": {
                "source": "verifier",
                "execution_status": execution_status or None,
                "issue_count": len(issues),
                "warning_count": len(warnings),
            },
        }

    def check_output_shape(self, execution_result: dict[str, Any]) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        if not isinstance(execution_result, dict):
            return [
                {
                    "code": "invalid_result_type",
                    "message": "execution_result must be a dictionary",
                }
            ]

        for field_name in self.REQUIRED_FIELDS:
            if field_name not in execution_result:
                issues.append(
                    {
                        "code": "missing_field",
                        "message": f"execution_result is missing '{field_name}'",
                    }
                )
        return issues

    def check_basic_consistency(
        self,
        execution_result: dict[str, Any],
        task_contract,
    ) -> dict[str, list[dict[str, str]]]:
        issues: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        status = execution_result.get("status")
        error = execution_result.get("error")
        output = execution_result.get("output")
        artifacts = execution_result.get("artifacts")
        tool_name = execution_result.get("tool_name")

        if status not in {"success", "error"}:
            issues.append(
                {
                    "code": "invalid_status",
                    "message": "status must be either 'success' or 'error'",
                }
            )
        if status == "success" and error is not None:
            issues.append(
                {
                    "code": "success_with_error",
                    "message": "successful execution_result must not include an error payload",
                }
            )
        if status == "error" and not error:
            issues.append(
                {
                    "code": "error_without_error_payload",
                    "message": "failed execution_result must include an error payload",
                }
            )
        if status == "success" and output is None:
            issues.append(
                {
                    "code": "missing_output",
                    "message": "successful execution_result must include output",
                }
            )
        if status == "error":
            issues.append(
                {
                    "code": "execution_failed",
                    "message": "execution_result reports a failed execution",
                }
            )
        if not tool_name:
            warnings.append(
                {
                    "code": "missing_tool_name",
                    "message": "tool_name is empty; later audit trails will be weaker",
                }
            )
        if not isinstance(artifacts, list):
            issues.append(
                {
                    "code": "invalid_artifacts",
                    "message": "artifacts must be a list",
                }
            )

        expected_artifacts = set(getattr(task_contract, "expected_artifacts", []))
        if status == "success" and "code_patch" in expected_artifacts and not artifacts:
            warnings.append(
                {
                    "code": "missing_expected_artifact",
                    "message": "task contract expects a code_patch but execution_result has no artifacts",
                }
            )

        return {"issues": issues, "warnings": warnings}

    def build_verification_report(
        self,
        *,
        passed: bool,
        issues: list[dict[str, str]],
        warnings: list[dict[str, str]],
        execution_result: dict[str, Any],
        task_contract,
    ) -> dict[str, Any]:
        return {
            "status": "passed" if passed else "failed",
            "passed": passed,
            "issues": issues,
            "warnings": warnings,
            "needs_followup": (not passed) or bool(warnings),
            "residual_risk_hint": "review" if warnings or issues else "low",
            "metadata": {
                "task_type": getattr(getattr(task_contract, "task_type", None), "value", None),
                "contract_id": getattr(task_contract, "contract_id", None),
                "execution_status": execution_result.get("status"),
                "issue_count": len(issues),
                "warning_count": len(warnings),
            },
        }

    def _normalize_risk_level(self, level: str | None) -> str:
        normalized = str(level or "").strip().lower()
        return normalized if normalized in {"low", "medium", "high"} else "medium"

    def _risk_level_to_index(self, level: str) -> int:
        return {"low": 0, "medium": 1, "high": 2}[self._normalize_risk_level(level)]

    def _risk_index_to_level(self, index: int) -> str:
        return {0: "low", 1: "medium", 2: "high"}.get(max(0, min(index, 2)), "medium")
