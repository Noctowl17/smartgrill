from __future__ import annotations

import os
from dataclasses import dataclass


def _integer(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} moet een geheel getal zijn") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    address: str = os.getenv("TOGRILL_ADDRESS", "C3:B3:63:51:60:7B")
    host: str = os.getenv("SMARTGRILL_HOST", "0.0.0.0")
    port: int = _integer("SMARTGRILL_PORT", 8000)
    reconnect_delay: int = _integer("RECONNECT_DELAY", 10)
    stale_after: int = _integer("STALE_AFTER", 15)


settings = Settings()
