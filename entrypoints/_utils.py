from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any
import json


def normalize_optional_string(value: object | None) -> str | None:
    """Strip and return None for empty strings."""
    text = str(value).strip() if value is not None else ""
    return text or None


def normalize_required_string(value: object | None) -> str:
    return normalize_optional_string(value) or ""


def normalize_string_list(value: object) -> list[str]:
    """Normalize a value to a list of non-empty stripped strings.
    Preserves order, does NOT deduplicate (caller decides).

    Note: archive_browse.py previously used a variant that accepted None,
    deduplicated via set(), and returned sorted(results). That behavior
    was intentionally replaced by this simpler, order-preserving version
    which already handles None by returning [].
    """
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        candidates = list(value)
    else:
        raise TypeError("expected a string or sequence of strings")
    return [str(c).strip() for c in candidates if str(c).strip()]


def normalize_string_list_sorted(value: object) -> list[str]:
    """Normalize a value to a deduplicated, sorted list of non-empty stripped strings.
    Used in archive_browse.py where the original local helper returned sorted+deduped results.
    """
    return sorted(set(normalize_string_list(value)))


def to_json_value(value: Any) -> Any:
    """Recursively convert dataclasses / enums to JSON-safe primitives."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: to_json_value(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(item) for item in value]
    return value


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)


def extract_mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        return dict(value)
    return {}
