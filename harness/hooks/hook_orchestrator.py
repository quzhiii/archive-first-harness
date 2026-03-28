from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Any

from harness.hooks.models import EVENT_PAYLOAD_TYPES, HOOK_EVENT_NAMES


class HookDispatchError(RuntimeError):
    """Raised when a registered hook handler fails during emit."""


class HookOrchestrator:
    """Keep hook delivery synchronous, local, and small.

    This object is only an in-process event multiplexer. It is not a plugin system,
    an async bus, or a new control plane.
    """

    MAX_RECENT_DISPATCHES = 50

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[object], Any]]] = {
            event_name: [] for event_name in sorted(HOOK_EVENT_NAMES)
        }
        self._recent_dispatches: deque[dict[str, Any]] = deque(
            maxlen=self.MAX_RECENT_DISPATCHES
        )

    def register(self, event_name: str, handler: Callable[[object], Any]) -> None:
        normalized_event_name = self._normalize_event_name(event_name)
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._handlers[normalized_event_name].append(handler)

    def unregister(self, event_name: str, handler: Callable[[object], Any]) -> None:
        normalized_event_name = self._normalize_event_name(event_name)
        handlers = self._handlers[normalized_event_name]
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event_name: str, payload: object) -> list[Any]:
        normalized_event_name = self._normalize_event_name(event_name)
        self._validate_payload(normalized_event_name, payload)

        handlers = self._handlers[normalized_event_name]
        handler_count = len(handlers)
        results: list[Any] = []
        for handler in handlers:
            try:
                results.append(handler(payload))
            except Exception as exc:
                self._record_dispatch(
                    event_name=normalized_event_name,
                    payload=payload,
                    handler_count=handler_count,
                    status="failed",
                    error_type=type(exc).__name__,
                )
                handler_name = self._handler_name(handler)
                raise HookDispatchError(
                    f"handler '{handler_name}' failed for event '{normalized_event_name}'"
                ) from exc

        self._record_dispatch(
            event_name=normalized_event_name,
            payload=payload,
            handler_count=handler_count,
            status="success",
            error_type=None,
        )
        return results

    def clear(self, event_name: str | None = None) -> None:
        if event_name is None:
            for registered_event in self._handlers:
                self._handlers[registered_event].clear()
            return

        normalized_event_name = self._normalize_event_name(event_name)
        self._handlers[normalized_event_name].clear()

    def list_handlers(self, event_name: str | None = None) -> dict[str, list[str]] | list[str]:
        if event_name is None:
            return {
                registered_event: [self._handler_name(handler) for handler in handlers]
                for registered_event, handlers in self._handlers.items()
            }

        normalized_event_name = self._normalize_event_name(event_name)
        return [
            self._handler_name(handler)
            for handler in self._handlers[normalized_event_name]
        ]

    def get_recent_dispatches(self, limit: int | None = None) -> list[dict[str, Any]]:
        dispatches = list(self._recent_dispatches)
        if limit is None:
            return dispatches
        if limit <= 0:
            return []
        return dispatches[-limit:]

    def _normalize_event_name(self, event_name: str) -> str:
        normalized = str(event_name).strip()
        if not normalized:
            raise ValueError("event_name must not be empty")
        if normalized not in HOOK_EVENT_NAMES:
            raise ValueError(f"unsupported event_name: {normalized}")
        return normalized

    def _validate_payload(self, event_name: str, payload: object) -> None:
        expected_type = EVENT_PAYLOAD_TYPES[event_name]
        if not isinstance(payload, expected_type):
            raise TypeError(
                f"payload for '{event_name}' must be {expected_type.__name__}"
            )

    def _record_dispatch(
        self,
        *,
        event_name: str,
        payload: object,
        handler_count: int,
        status: str,
        error_type: str | None,
    ) -> None:
        self._recent_dispatches.append(
            {
                "event_name": event_name,
                "event_id": getattr(payload, "event_id", None),
                "handler_count": handler_count,
                "status": status,
                "error_type": error_type,
                "timestamp": getattr(payload, "timestamp", None),
            }
        )

    def _handler_name(self, handler: Callable[[object], Any]) -> str:
        return getattr(handler, "__name__", handler.__class__.__name__)

