from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class Settings:
    default_model_slot: str
    artifacts_dir: Path
    sandbox_enabled: bool
    telemetry_enabled: bool
    default_token_budget: str
    default_latency_budget: str


_ENV_PREFIX = "AI_HARNESS_"


def load_settings() -> Settings:
    artifacts_dir = Path(
        os.getenv(f"{_ENV_PREFIX}ARTIFACTS_DIR", "artifacts")
    )
    return Settings(
        default_model_slot=os.getenv(f"{_ENV_PREFIX}DEFAULT_MODEL_SLOT", "default"),
        artifacts_dir=artifacts_dir,
        sandbox_enabled=_read_bool(f"{_ENV_PREFIX}SANDBOX_ENABLED", True),
        telemetry_enabled=_read_bool(f"{_ENV_PREFIX}TELEMETRY_ENABLED", True),
        default_token_budget=os.getenv(f"{_ENV_PREFIX}DEFAULT_TOKEN_BUDGET", "low"),
        default_latency_budget=os.getenv(f"{_ENV_PREFIX}DEFAULT_LATENCY_BUDGET", "low"),
    )


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
