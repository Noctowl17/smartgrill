from __future__ import annotations

import asyncio
import logging

from bleak import BleakScanner
from togrill_bluetooth.client import Client
from togrill_bluetooth.packets import Packet, PacketA0Notify, PacketA1Notify

from .config import settings
from .state import GrillState

LOGGER = logging.getLogger(__name__)


class ToGrillWorker:
    def __init__(self, state: GrillState) -> None:
        self.state = state
        self._loop: asyncio.AbstractEventLoop | None = None
        self._disconnected = asyncio.Event()

    def _notification(self, packet: Packet) -> None:
        if self._loop is None:
            return
        if isinstance(packet, PacketA0Notify):
            self._loop.create_task(self.state.set_battery(packet.battery))
            LOGGER.info(
                "Apparaatinfo: batterij=%s%% probes=%s ambient=%s",
                packet.battery,
                packet.probe_count,
                packet.ambient,
            )
        elif isinstance(packet, PacketA1Notify):
            temperatures = list(packet.temperatures)
            self._loop.create_task(self.state.set_temperatures(temperatures))
            LOGGER.info("Temperaturen ontvangen: %s", temperatures)

    def _on_disconnect(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._disconnected.set)

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()

        while True:
            client: Client | None = None
            self._disconnected.clear()
            try:
                await self.state.set_connection(False, None)
                LOGGER.info("Zoeken naar AT-02 op %s", settings.address)

                device = await BleakScanner.find_device_by_address(
                    settings.address,
                    timeout=20.0,
                )
                if device is None:
                    raise RuntimeError(f"AT-02 {settings.address} niet gevonden")

                LOGGER.info("Verbinden met %s", settings.address)
                client = await Client.connect(
                    device,
                    notify_callback=self._notification,
                    disconnected_callback=self._on_disconnect,
                )
                await self.state.set_connection(True, None)
                LOGGER.info("Verbonden met AT-02")

                await client.request(PacketA0Notify)
                await client.request(PacketA1Notify)

                while client.is_connected and not self._disconnected.is_set():
                    await asyncio.sleep(1)

                raise ConnectionError("Bluetoothverbinding verbroken")

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOGGER.exception("Bluetoothfout")
                await self.state.set_connection(False, str(exc))
            finally:
                if client is not None and client.is_connected:
                    try:
                        await client.disconnect()
                    except Exception:
                        LOGGER.exception("Kon Bluetoothverbinding niet netjes sluiten")
                await self.state.set_connection(False)

            await asyncio.sleep(settings.reconnect_delay)
