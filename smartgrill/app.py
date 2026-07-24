from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .alerts import AlertMonitor, alert_settings
from .bluetooth import ToGrillWorker
from .config import settings
from .push import PushService
from .state import GrillState

BASE_DIR = Path(__file__).resolve().parent
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

state = GrillState(settings.address)
worker = ToGrillWorker(state)
push_service = PushService()
alert_monitor = AlertMonitor(state, alert_settings, push_service)


@asynccontextmanager
async def lifespan(_: FastAPI):
    tasks = [
        asyncio.create_task(worker.run(), name="togrill-bluetooth"),
        asyncio.create_task(alert_monitor.run(), name="smartgrill-alerts"),
    ]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="SmartGrill", version="0.2.0-beta.1", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/settings", include_in_schema=False)
async def settings_page() -> FileResponse:
    return FileResponse(BASE_DIR / "templates" / "settings.html")


@app.get("/service-worker.js", include_in_schema=False)
async def service_worker() -> FileResponse:
    return FileResponse(
        BASE_DIR / "static" / "service-worker.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/status")
async def api_status():
    return await state.snapshot()


@app.get("/api/settings")
async def api_get_settings():
    return settings.public()


@app.post("/api/settings")
async def api_update_settings(payload: dict[str, Any] = Body(...)):
    previous_address = settings.address

    try:
        settings.update(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logging.exception("Kon SmartGrill-instellingen niet opslaan")
        raise HTTPException(
            status_code=500,
            detail="De instellingen konden niet worden opgeslagen",
        ) from exc

    response = settings.public()
    response["restart_required"] = settings.address != previous_address
    return response


@app.get("/api/alerts")
async def api_get_alerts():
    return alert_settings.public()


@app.post("/api/alerts")
async def api_update_alerts(payload: dict[str, Any] = Body(...)):
    try:
        alert_settings.update(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logging.exception("Kon alarmgrenzen niet opslaan")
        raise HTTPException(
            status_code=500,
            detail="De alarmgrenzen konden niet worden opgeslagen",
        ) from exc
    return alert_settings.public()


@app.get("/api/push/public-key")
async def api_push_public_key():
    return {
        "public_key": push_service.public_key,
        "subscriptions": await push_service.subscription_count(),
    }


@app.post("/api/push/subscribe")
async def api_push_subscribe(payload: dict[str, Any] = Body(...)):
    try:
        await push_service.subscribe(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"subscribed": True}


@app.delete("/api/push/subscribe")
async def api_push_unsubscribe(payload: dict[str, Any] = Body(...)):
    endpoint = str(payload.get("endpoint", "")).strip()
    if not endpoint:
        raise HTTPException(status_code=400, detail="Pushendpoint ontbreekt")
    await push_service.unsubscribe(endpoint)
    return {"subscribed": False}


@app.post("/api/push/test")
async def api_push_test(payload: dict[str, Any] = Body(default={})):
    notification = {
        "title": "SmartGrill-testmelding",
        "body": "Pushmeldingen werken. Je mist geen temperatuurgrens meer.",
        "url": "/settings",
        "tag": "smartgrill:test",
    }
    endpoint = str(payload.get("endpoint", "")).strip()
    try:
        if endpoint:
            delivered = 1 if await push_service.send_to(endpoint, notification) else 0
        else:
            delivered = await push_service.broadcast(notification)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("Testmelding kon niet worden verstuurd")
        raise HTTPException(
            status_code=502,
            detail=f"Testmelding mislukt: {exc}",
        ) from exc
    if delivered == 0:
        raise HTTPException(
            status_code=409,
            detail="Er zijn nog geen actieve pushabonnementen",
        )
    return {"delivered": delivered}


@app.get("/api/health")
async def api_health():
    data = await state.snapshot()
    age_seconds = None
    fresh = False
    if data["last_update"]:
        last = datetime.fromisoformat(data["last_update"])
        age_seconds = round((datetime.now().astimezone() - last).total_seconds(), 1)
        fresh = age_seconds <= settings.stale_after

    return {
        "status": "ok" if data["connected"] and fresh else "degraded",
        "bluetooth_connected": data["connected"],
        "data_fresh": fresh,
        "age_seconds": age_seconds,
        "last_update": data["last_update"],
    }
