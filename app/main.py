from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import chat, health, pricing, slots
from app.db import engine
from app.tracing import get_tracer

UI_DIST = Path(__file__).resolve().parent.parent / "ui" / "dist" / "ui" / "browser"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_tracer()
    yield
    tracer = get_tracer()
    if tracer:
        tracer.flush()
    engine.dispose()


app = FastAPI(title="service-agent", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(slots.router)
app.include_router(pricing.router)
app.include_router(chat.router)

if UI_DIST.exists():
    app.mount("/", StaticFiles(directory=UI_DIST, html=True), name="ui")

