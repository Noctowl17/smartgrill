from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


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


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


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


class AlertMonitorTests(unittest.IsolatedAsyncioTestCase):
    def create_settings(self) -> AlertSettings:
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
                "alarm_interval_minutes": 5,
            },
            save=False,
        )
        return alert_settings

    async def test_temperature_alert_repeats_at_configured_interval(self):
        alert_settings = self.create_settings()
        push = FakePush()
        monitor = AlertMonitor(FakeState(), alert_settings, push)
        clock = FakeClock()

        with patch("smartgrill.alerts.monotonic", clock):
            await monitor.evaluate(snapshot(69))
            await monitor.evaluate(snapshot(70))
            clock.advance(299)
            await monitor.evaluate(snapshot(72))
            clock.advance(1)
            await monitor.evaluate(snapshot(73))

        self.assertEqual(len(push.messages), 2)
        self.assertEqual(push.messages[0]["tag"], "probe_1:maximum")
        self.assertIn("70.0 °C", push.messages[0]["body"])
        self.assertEqual(push.messages[1]["tag"], "probe_1:maximum")
        self.assertIn("73.0 °C", push.messages[1]["body"])

    async def test_temperature_alert_resets_as_soon_as_value_is_in_range(self):
        alert_settings = self.create_settings()
        push = FakePush()
        monitor = AlertMonitor(FakeState(), alert_settings, push)
        clock = FakeClock()

        with patch("smartgrill.alerts.monotonic", clock):
            await monitor.evaluate(snapshot(70))
            await monitor.evaluate(snapshot(69.9))
            await monitor.evaluate(snapshot(70))

        self.assertEqual(len(push.messages), 2)
        self.assertEqual(push.messages[0]["tag"], "probe_1:maximum")
        self.assertEqual(push.messages[1]["tag"], "probe_1:maximum")

    async def test_minimum_temperature_alert_also_repeats(self):
        alert_settings = self.create_settings()
        alert_settings.update(
            {
                "sensors": {
                    "probe_1": {
                        "enabled": True,
                        "minimum": 60,
                        "maximum": None,
                    },
                },
            },
            save=False,
        )
        push = FakePush()
        monitor = AlertMonitor(FakeState(), alert_settings, push)
        clock = FakeClock()

        with patch("smartgrill.alerts.monotonic", clock):
            await monitor.evaluate(snapshot(60))
            clock.advance(300)
            await monitor.evaluate(snapshot(58))

        self.assertEqual(len(push.messages), 2)
        self.assertEqual(push.messages[0]["tag"], "probe_1:minimum")
        self.assertIn("60.0 °C", push.messages[0]["body"])
        self.assertEqual(push.messages[1]["tag"], "probe_1:minimum")
        self.assertIn("58.0 °C", push.messages[1]["body"])

    async def test_battery_and_connection_alerts_do_not_repeat(self):
        alert_settings = self.create_settings()
        push = FakePush()
        monitor = AlertMonitor(FakeState(), alert_settings, push)

        await monitor.evaluate(snapshot(69))
        await monitor.evaluate(snapshot(69, battery=10))
        await monitor.evaluate(snapshot(69, battery=10))
        await monitor.evaluate(snapshot(69, battery=10, connected=False))
        await monitor.evaluate(snapshot(69, battery=10, connected=False))

        self.assertEqual(len(push.messages), 2)
        self.assertEqual(push.messages[0]["tag"], "battery:minimum")
        self.assertEqual(push.messages[1]["tag"], "connection:lost")


if __name__ == "__main__":
    unittest.main()
