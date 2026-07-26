from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


class _PlaceholderPushService:
    pass


fake_push_module = types.ModuleType("smartgrill.push")
fake_push_module.PushService = _PlaceholderPushService
sys.modules.setdefault("smartgrill.push", fake_push_module)

temporary_directory = tempfile.TemporaryDirectory()
os.environ["SMARTGRILL_ALERTS_CONFIG"] = str(
    Path(temporary_directory.name) / "alerts.json",
)

from smartgrill.alerts import AlertMonitor, AlertSettings  # noqa: E402


class FakeState:
    async def snapshot(self):
        return {}


class FakePush:
    def __init__(self) -> None:
        self.messages = []

    async def broadcast(self, payload):
        self.messages.append(payload)
        return 1


class AlertMonitorTests(unittest.IsolatedAsyncioTestCase):
    async def test_thresholds_only_notify_on_a_new_crossing(self):
        alert_settings = AlertSettings()
        alert_settings.update(
            {
                "sensors": {
                    "probe_1": {
                        "enabled": True,
                        "minimum": None,
                        "maximum": 70,
                    },
                },
                "battery": {"enabled": True, "minimum": 15},
                "connection_lost": True,
                "hysteresis": 1,
            },
        )
        push = FakePush()
        monitor = AlertMonitor(FakeState(), alert_settings, push)

        def snapshot(temperature, battery=50, connected=True):
            return {
                "connected": connected,
                "battery": battery,
                "temperatures": {
                    "kamado": None,
                    "probe_1": temperature,
                    "probe_2": None,
                    "probe_3": None,
                    "probe_4": None,
                },
            }

        await monitor.evaluate(snapshot(69))
        await monitor.evaluate(snapshot(70))
        await monitor.evaluate(snapshot(71))
        await monitor.evaluate(snapshot(68, battery=10))
        await monitor.evaluate(snapshot(70, battery=10))
        await monitor.evaluate(snapshot(70, battery=10, connected=False))

        self.assertEqual(len(push.messages), 4)
        self.assertEqual(push.messages[0]["tag"], "probe_1:maximum")
        self.assertEqual(push.messages[1]["tag"], "battery:minimum")
        self.assertEqual(push.messages[2]["tag"], "probe_1:maximum")
        self.assertEqual(push.messages[3]["tag"], "connection:lost")


if __name__ == "__main__":
    unittest.main()
