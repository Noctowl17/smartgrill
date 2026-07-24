from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(
    os.getenv("SMARTGRILL_DATA_DIR", BASE_DIR.parent / "data"),
)
DEFAULT_VAPID_SUBJECT = "https://github.com/Noctowl17/smartgrill"


def _vapid_subject() -> str:
    subject = os.getenv("VAPID_SUBJECT", DEFAULT_VAPID_SUBJECT).strip()
    parsed = urlparse(subject)

    if parsed.scheme == "mailto":
        address = parsed.path
        if "@" in address and not any(character.isspace() for character in address):
            domain = address.rsplit("@", 1)[1].lower()
            if domain != "localhost" and not domain.endswith(".local"):
                return subject

    if parsed.scheme == "https" and parsed.netloc:
        hostname = (parsed.hostname or "").lower()
        if hostname != "localhost" and not hostname.endswith(".local"):
            return subject

    raise RuntimeError(
        "VAPID_SUBJECT moet een publiek https-adres of mailto-adres zijn; "
        "localhost- en .local-adressen worden door Apple Web Push geweigerd"
    )


class PushService:
    def __init__(self) -> None:
        self.data_dir = DATA_DIR
        self.private_key_path = self.data_dir / "vapid_private.pem"
        self.subscriptions_path = self.data_dir / "push_subscriptions.json"
        self.subject = _vapid_subject()
        self._lock = asyncio.Lock()

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._vapid = self._load_or_create_vapid()
        self.public_key = self._application_server_key(self._vapid)

    def _load_or_create_vapid(self) -> Vapid:
        if self.private_key_path.exists():
            return Vapid.from_file(str(self.private_key_path))

        vapid = Vapid()
        vapid.generate_keys()
        vapid.save_key(str(self.private_key_path))
        try:
            self.private_key_path.chmod(0o600)
        except OSError:
            LOGGER.warning("Kon bestandsrechten van de VAPID-sleutel niet aanpassen")
        LOGGER.info("Nieuwe VAPID-sleutel voor Web Push aangemaakt")
        return vapid

    @staticmethod
    def _application_server_key(vapid: Vapid) -> str:
        raw = vapid.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    def _load_subscriptions(self) -> list[dict[str, Any]]:
        if not self.subscriptions_path.exists():
            return []
        try:
            data = json.loads(self.subscriptions_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            LOGGER.exception("Pushabonnementen konden niet worden gelezen")
            return []
        return data if isinstance(data, list) else []

    def _save_subscriptions(self, subscriptions: list[dict[str, Any]]) -> None:
        temporary = self.subscriptions_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(subscriptions, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.subscriptions_path)

    @staticmethod
    def validate_subscription(subscription: dict[str, Any]) -> dict[str, Any]:
        endpoint = str(subscription.get("endpoint", "")).strip()
        keys = subscription.get("keys")
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Ongeldig pushendpoint")
        if not isinstance(keys, dict):
            raise ValueError("Pushsleutels ontbreken")

        p256dh = str(keys.get("p256dh", "")).strip()
        auth = str(keys.get("auth", "")).strip()
        if not p256dh or not auth:
            raise ValueError("Pushsleutels zijn onvolledig")

        return {
            "endpoint": endpoint,
            "expirationTime": subscription.get("expirationTime"),
            "keys": {
                "p256dh": p256dh,
                "auth": auth,
            },
        }

    async def subscribe(self, subscription: dict[str, Any]) -> None:
        validated = self.validate_subscription(subscription)
        async with self._lock:
            subscriptions = self._load_subscriptions()
            subscriptions = [
                existing
                for existing in subscriptions
                if existing.get("endpoint") != validated["endpoint"]
            ]
            subscriptions.append(validated)
            self._save_subscriptions(subscriptions)

    async def unsubscribe(self, endpoint: str) -> None:
        async with self._lock:
            subscriptions = self._load_subscriptions()
            filtered = [
                item for item in subscriptions if item.get("endpoint") != endpoint
            ]
            if len(filtered) != len(subscriptions):
                self._save_subscriptions(filtered)

    def _send_sync(
        self,
        subscription: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=str(self.private_key_path),
            vapid_claims={"sub": self.subject},
            ttl=300,
        )

    async def send_to(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> bool:
        async with self._lock:
            subscription = next(
                (
                    item
                    for item in self._load_subscriptions()
                    if item.get("endpoint") == endpoint
                ),
                None,
            )

        if subscription is None:
            raise ValueError("Dit pushabonnement is niet geregistreerd")

        try:
            await asyncio.to_thread(self._send_sync, subscription, payload)
            return True
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in {404, 410}:
                await self.unsubscribe(endpoint)
            LOGGER.warning("Web Push naar %s mislukt: %s", endpoint, exc)
            raise

    async def broadcast(self, payload: dict[str, Any]) -> int:
        async with self._lock:
            subscriptions = self._load_subscriptions()

        delivered = 0
        for subscription in subscriptions:
            endpoint = str(subscription.get("endpoint", ""))
            try:
                await asyncio.to_thread(self._send_sync, subscription, payload)
                delivered += 1
            except WebPushException as exc:
                status = getattr(exc.response, "status_code", None)
                if status in {404, 410}:
                    await self.unsubscribe(endpoint)
                LOGGER.warning("Web Push naar %s mislukt: %s", endpoint, exc)
            except Exception:
                LOGGER.exception("Onverwachte fout bij versturen van Web Push")
        return delivered

    async def subscription_count(self) -> int:
        async with self._lock:
            return len(self._load_subscriptions())
