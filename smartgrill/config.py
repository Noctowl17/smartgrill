from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.getenv("SMARTGRILL_CONFIG", BASE_DIR.parent / "config.json"))
DEFAULT_PROBE_NAMES = ["Ambiance", "Probe 1", "Probe 2", "Probe 3", "Probe 4"]


def _integer(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} moet een geheel getal zijn") from exc


@dataclass(slots=True)
class Settings:
    address: str = os.getenv("TOGRILL_ADDRESS", "")
    host: str = os.getenv("SMARTGRILL_HOST", "0.0.0.0")
    port: int = _integer("SMARTGRILL_PORT", 8000)
    reconnect_delay: int = _integer("RECONNECT_DELAY", 10)
    stale_after: int = _integer("STALE_AFTER", 15)
    probe_names: list[str] = field(default_factory=lambda: DEFAULT_PROBE_NAMES.copy())

    @property
    def configured(self) -> bool:
        return bool(self.address.strip())

    def public(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "configured": self.configured,
            "reconnect_delay": self.reconnect_delay,
            "stale_after": self.stale_after,
            "probe_names": self.probe_names,
        }

    def update(self, data: dict[str, Any]) -> None:
        address = str(data.get("address", self.address)).strip().upper()
        if address and len(address.split(":")) != 6:
            raise ValueError("Ongeldig Bluetooth MAC-adres")

        reconnect_delay = int(data.get("reconnect_delay", self.reconnect_delay))
        stale_after = int(data.get("stale_after", self.stale_after))
        if reconnect_delay < 1 or reconnect_delay > 300:
            raise ValueError("Reconnect-interval moet tussen 1 en 300 seconden liggen")
        if stale_after < 5 or stale_after > 600:
            raise ValueError("Verouderingsgrens moet tussen 5 en 600 seconden liggen")

        names = data.get("probe_names", self.probe_names)
        if not isinstance(names, list) or len(names) != 5:
            raise ValueError("Er moeten precies vijf probe-namen worden opgegeven")

        self.address = address
        self.reconnect_delay = reconnect_delay
        self.stale_after = stale_after
        self.probe_names = [
            str(name).strip() or DEFAULT_PROBE_NAMES[index]
            for index, name in enumerate(names)
        ]
        self.save()

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = CONFIG_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        temporary.replace(CONFIG_PATH)


def load_settings() -> Settings:
    loaded = Settings()
    if not CONFIG_PATH.exists():
        return loaded

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        loaded.update(data)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Kan configuratie {CONFIG_PATH} niet laden: {exc}") from exc
    return loaded


settings = load_settings()
