from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .bluetooth import ToGrillWorker
from .config import settings
from .state import GrillState

BASE_DIR = Path(__file__).resolve().parent
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

state = GrillState(settings.address)
worker = ToGrillWorker(state)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(worker.run(), name="togrill-bluetooth")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="SmartGrill", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/api/status")
async def api_status():
    return await state.snapshot()


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
