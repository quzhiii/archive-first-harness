from __future__ import annotations

from typing import Any

from harness.sandbox.rollback import RollbackManager


class SandboxExecutor:
    """Wrap a stubbed action in a minimal isolation and snapshot boundary."""

    def __init__(self, rollback_manager: RollbackManager | None = None) -> None:
        self.rollback_manager = rollback_manager or RollbackManager()

    def execute(
        self,
        action: str,
        payload: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        sanitized_payload = self._sanitize_payload(payload)
        rollback_target = payload.get("rollback_target")
        snapshot_ref = self.snapshot_before(action, payload)
        if isinstance(rollback_target, dict):
            rollback_target["sandbox_action"] = action
            rollback_target["status"] = "running"

        if dry_run:
            if isinstance(rollback_target, dict):
                rollback_target["status"] = "dry_run"
            return self.format_sandbox_result(
                status="success",
                action=action,
                payload=sanitized_payload,
                output={"dry_run": True, "summary": f"dry-run:{action}"},
                error=None,
                snapshot_ref=snapshot_ref,
                metadata={"dry_run": True, "isolated": True, "runner_used": False},
            )

        if payload.get("should_fail"):
            if isinstance(rollback_target, dict):
                rollback_target["status"] = "failed"
            return self.format_sandbox_result(
                status="error",
                action=action,
                payload=sanitized_payload,
                output=None,
                error={
                    "type": "sandbox_execution_failed",
                    "message": f"mock action '{action}' failed inside sandbox",
                },
                snapshot_ref=snapshot_ref,
                metadata={"dry_run": False, "isolated": True, "runner_used": False},
            )

        runner = payload.get("runner")
        if callable(runner):
            try:
                runner_output = runner()
            except Exception as exc:
                if isinstance(rollback_target, dict):
                    rollback_target["status"] = "failed"
                return self.format_sandbox_result(
                    status="error",
                    action=action,
                    payload=sanitized_payload,
                    output=None,
                    error={"type": type(exc).__name__, "message": str(exc)},
                    snapshot_ref=snapshot_ref,
                    metadata={"dry_run": False, "isolated": True, "runner_used": True},
                )

            output = {"execution_result": runner_output}
            derived_status = "success"
            derived_error = None
            if isinstance(runner_output, dict) and runner_output.get("status") == "error":
                derived_status = "error"
                derived_error = dict(
                    runner_output.get("error")
                    or {
                        "type": "sandbox_execution_failed",
                        "message": f"action '{action}' returned an error inside sandbox",
                    }
                )

            if isinstance(rollback_target, dict):
                rollback_target["status"] = "failed" if derived_status == "error" else "completed"

            return self.format_sandbox_result(
                status=derived_status,
                action=action,
                payload=sanitized_payload,
                output=output,
                error=derived_error,
                snapshot_ref=snapshot_ref,
                metadata={"dry_run": False, "isolated": True, "runner_used": True},
            )

        if isinstance(rollback_target, dict):
            rollback_target["status"] = "completed"
        return self.format_sandbox_result(
            status="success",
            action=action,
            payload=sanitized_payload,
            output={"summary": f"executed:{action}", "echo": sanitized_payload},
            error=None,
            snapshot_ref=snapshot_ref,
            metadata={"dry_run": False, "isolated": True, "runner_used": False},
        )

    def snapshot_before(self, action_id: str, payload: dict[str, Any]) -> str:
        target = payload.get("rollback_target")
        if target is None:
            target = {"action": action_id, "payload": self._sanitize_payload(payload)}
        snapshot = self.rollback_manager.create_snapshot(target)
        return snapshot["snapshot_ref"]

    def format_sandbox_result(
        self,
        *,
        status: str,
        action: str,
        payload: dict[str, Any],
        output: dict[str, Any] | None,
        error: dict[str, Any] | None,
        snapshot_ref: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": status,
            "action": action,
            "payload": dict(payload),
            "output": output,
            "error": error,
            "snapshot_ref": snapshot_ref,
            "metadata": metadata,
        }

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in payload.items()
            if key not in {"runner", "rollback_target"}
        }
