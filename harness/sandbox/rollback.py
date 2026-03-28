from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class RollbackManager:
    """Keep minimal in-memory snapshots and restore a single target."""

    def __init__(self) -> None:
        self._snapshots: dict[str, dict[str, Any]] = {}

    def create_snapshot(self, target: Any) -> dict[str, Any]:
        snapshot_ref = f"snapshot-{uuid4().hex}"
        self._snapshots[snapshot_ref] = {
            "target_ref": target,
            "state": deepcopy(target),
            "created_at": datetime.now(UTC).isoformat(),
        }
        return {
            "status": "created",
            "snapshot_ref": snapshot_ref,
            "created_at": self._snapshots[snapshot_ref]["created_at"],
        }

    def rollback(self, snapshot_ref: str) -> dict[str, Any]:
        snapshot = self._snapshots.get(snapshot_ref)
        if snapshot is None:
            return {
                "status": "error",
                "snapshot_ref": snapshot_ref,
                "error": {
                    "type": "unknown_snapshot",
                    "message": f"snapshot '{snapshot_ref}' does not exist",
                },
            }

        target_ref = snapshot["target_ref"]
        restored_state = deepcopy(snapshot["state"])
        if isinstance(target_ref, dict):
            target_ref.clear()
            target_ref.update(restored_state)
        elif isinstance(target_ref, list):
            target_ref.clear()
            target_ref.extend(restored_state)
        else:
            return {
                "status": "error",
                "snapshot_ref": snapshot_ref,
                "error": {
                    "type": "unsupported_target",
                    "message": (
                        "rollback only supports dictionary and list targets in v0.3"
                    ),
                },
            }

        return {
            "status": "rolled_back",
            "snapshot_ref": snapshot_ref,
            "restored_state": restored_state,
        }

    def describe_snapshot(self, snapshot_ref: str) -> dict[str, Any]:
        snapshot = self._snapshots.get(snapshot_ref)
        if snapshot is None:
            return {
                "status": "error",
                "snapshot_ref": snapshot_ref,
                "error": {
                    "type": "unknown_snapshot",
                    "message": f"snapshot '{snapshot_ref}' does not exist",
                },
            }

        state = snapshot["state"]
        return {
            "status": "ok",
            "snapshot_ref": snapshot_ref,
            "created_at": snapshot["created_at"],
            "target_type": type(state).__name__,
        }
