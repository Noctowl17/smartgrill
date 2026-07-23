from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime
from typing import Any


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class GrillState:
    def __init__(self, address: str) -> None:
        self._lock = asyncio.Lock()
        self._data: dict[str, Any] = {
            "device": "AT-02",
            "address": address,
            "connected": False,
            "battery": None,
            "last_update": None,
            "last_error": None,
            "temperatures": {
                "kamado": None,
                "probe_1": None,
                "probe_2": None,
                "probe_3": None,
                "probe_4": None,
            },
        }

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return deepcopy(self._data)

    async def set_connection(self, connected: bool, error: str | None = None) -> None:
        async with self._lock:
            self._data["connected"] = connected
            self._data["last_error"] = error

    async def set_battery(self, battery: int | None) -> None:
        async with self._lock:
            self._data["battery"] = battery

    async def set_temperatures(self, values: list[float | None]) -> None:
        padded = list(values[:7])
        padded.extend([None] * (7 - len(padded)))

        def clean(value: float | None) -> float | None:
            if value is None:
                return None
            number = float(value)
            if number < -50 or number > 400:
                return None
            return round(number, 1)

        async with self._lock:
            self._data["temperatures"] = {
                # AT-02 mapping verified on the user's unit:
                # indexes 0-3 = probe 1-4, index 6 = ambient/kamado.
                "kamado": clean(padded[6]),
                "probe_1": clean(padded[0]),
                "probe_2": clean(padded[1]),
                "probe_3": clean(padded[2]),
                "probe_4": clean(padded[3]),
            }
            self._data["last_update"] = now_iso()
            self._data["last_error"] = None
