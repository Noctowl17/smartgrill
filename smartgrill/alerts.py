from __future__ import annotations

import asyncio
import json
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .config import settings
from .push import PushService
from .state import GrillState

LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
ALERTS_PATH = Path(
    os.getenv("SMARTGRILL_ALERTS_CONFIG", BASE_DIR.parent / "alerts.json"),
)
SENSOR_KEYS = ["kamado", "probe_1", "probe_2", "probe_3", "probe_4"]
DEFAULT_SENSOR_ALERT = {
    "enabled": False,
    "minimum": None,
    "maximum": None,
}
DEFAULT_ALERTS: dict[str, Any] = {
    "sensors": {
        key: deepcopy(DEFAULT_SENSOR_ALERT)
        for key in SENSOR_KEYS
    },
    "battery": {
        "enabled": False,
        "minimum": 15,
    },
    "connection_lost": False,
    "hysteresis": 1.0,
}


def _optional_number(
    value: Any,
    *,
    minimum: float,
    maximum: float,
    label: str,
) -> float | None:
    if value is None or value == "":
        return None
    number = float(value)
    if number < minimum or number > maximum:
        raise ValueError(f"{label} moet tussen {minimum:g} en {maximum:g} liggen")
    return round(number, 1)


class AlertSettings:
    def __init__(self) -> None:
        self._data = deepcopy(DEFAULT_ALERTS)
        self.load()

    def load(self) -> None:
        if not ALERTS_PATH.exists():
            return
        try:
            data = json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
            self.update(data, save=False)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            LOGGER.exception("Alarmconfiguratie kon niet worden geladen")

    def public(self) -> dict[str, Any]:
        data = deepcopy(self._data)
        data["probe_names"] = settings.probe_names.copy()
        return data

    def update(self, data: dict[str, Any], *, save: bool = True) -> None:
        incoming_sensors = data.get("sensors", {})
        if not isinstance(incoming_sensors, dict):
            raise ValueError("Ongeldige sensorgrenzen")

        sensors: dict[str, dict[str, Any]] = {}
        for key in SENSOR_KEYS:
            current = self._data["sensors"][key]
            incoming = incoming_sensors.get(key, current)
            if not isinstance(incoming, dict):
                raise ValueError(f"Ongeldige grenzen voor {key}")

            minimum = _optional_number(
                incoming.get("minimum"),
                minimum=-50,
                maximum=400,
                label="Minimumtemperatuur",
            )
            maximum = _optional_number(
                incoming.get("maximum"),
                minimum=-50,
                maximum=400,
                label="Maximumtemperatuur",
            )
            if minimum is not None and maximum is not None and minimum >= maximum:
                raise ValueError(
                    "De minimumtemperatuur moet lager zijn dan de maximumtemperatuur",
                )
            sensors[key] = {
                "enabled": bool(incoming.get("enabled", False)),
                "minimum": minimum,
                "maximum": maximum,
            }

        incoming_battery = data.get("battery", self._data["battery"])
        if not isinstance(incoming_battery, dict):
            raise ValueError("Ongeldige batterijgrens")
        battery_minimum = _optional_number(
            incoming_battery.get("minimum", 15),
            minimum=0,
            maximum=100,
            label="Batterijgrens",
        )

        hysteresis = float(data.get("hysteresis", self._data["hysteresis"]))
        if hysteresis < 0.1 or hysteresis > 20:
            raise ValueError("Hysterese moet tussen 0,1 en 20 °C liggen")

        self._data = {
            "sensors": sensors,
            "battery": {
                "enabled": bool(incoming_battery.get("enabled", False)),
                "minimum": battery_minimum,
            },
            "connection_lost": bool(
                data.get("connection_lost", self._data["connection_lost"]),
            ),
            "hysteresis": round(hysteresis, 1),
        }
        if save:
            self.save()

    def save(self) -> None:
        ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = ALERTS_PATH.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._data, indent=2),
            encoding="utf-8",
        )
        temporary.replace(ALERTS_PATH)


class AlertMonitor:
    def __init__(
        self,
        state: GrillState,
        alert_settings: AlertSettings,
        push_service: PushService,
    ) -> None:
        self.state = state
        self.settings = alert_settings
        self.push = push_service
        self._active: set[str] = set()
        self._has_connected = False
        self._was_connected = False

    async def run(self) -> None:
        while True:
            try:
                await self.evaluate(await self.state.snapshot())
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Fout in SmartGrill-alarmcontrole")
            await asyncio.sleep(2)

    async def _threshold(
        self,
        *,
        key: str,
        active: bool,
        reset: bool,
        title: str,
        body: str,
    ) -> None:
        if active and key not in self._active:
            self._active.add(key)
            await self.push.broadcast(
                {
                    "title": title,
                    "body": body,
                    "url": "/",
                    "tag": key,
                },
            )
        elif reset:
            self._active.discard(key)

    async def evaluate(self, snapshot: dict[str, Any]) -> None:
        config = self.settings.public()
        hysteresis = float(config["hysteresis"])
        temperatures = snapshot.get("temperatures", {})

        for index, sensor_key in enumerate(SENSOR_KEYS):
            sensor = config["sensors"][sensor_key]
            value = temperatures.get(sensor_key)
            if not sensor["enabled"] or value is None:
                self._active.discard(f"{sensor_key}:minimum")
                self._active.discard(f"{sensor_key}:maximum")
                continue

            value = float(value)
            label = settings.probe_names[index]
            minimum = sensor["minimum"]
            maximum = sensor["maximum"]

            if minimum is not None:
                await self._threshold(
                    key=f"{sensor_key}:minimum",
                    active=value <= minimum,
                    reset=value >= minimum + hysteresis,
                    title=f"{label} is te koud",
                    body=f"{label} is {value:.1f} °C (minimum {minimum:.1f} °C).",
                )
            if maximum is not None:
                await self._threshold(
                    key=f"{sensor_key}:maximum",
                    active=value >= maximum,
                    reset=value <= maximum - hysteresis,
                    title=f"{label} heeft de grens bereikt",
                    body=f"{label} is {value:.1f} °C (grens {maximum:.1f} °C).",
                )

        battery = snapshot.get("battery")
        battery_config = config["battery"]
        battery_minimum = battery_config["minimum"]
        if (
            battery_config["enabled"]
            and battery is not None
            and battery_minimum is not None
        ):
            battery_value = float(battery)
            await self._threshold(
                key="battery:minimum",
                active=battery_value <= battery_minimum,
                reset=battery_value >= min(100, battery_minimum + 5),
                title="SmartGrill-batterij is bijna leeg",
                body=f"De batterij is nog {battery_value:.0f}%.",
            )
        else:
            self._active.discard("battery:minimum")

        connected = bool(snapshot.get("connected"))
        if connected:
            self._has_connected = True
            self._active.discard("connection:lost")
        elif (
            config["connection_lost"]
            and self._has_connected
            and self._was_connected
            and "connection:lost" not in self._active
        ):
            self._active.add("connection:lost")
            await self.push.broadcast(
                {
                    "title": "SmartGrill-verbinding verbroken",
                    "body": "De AT-02 is niet meer via Bluetooth verbonden.",
                    "url": "/",
                    "tag": "connection:lost",
                },
            )
        self._was_connected = connected


alert_settings = AlertSettings()
