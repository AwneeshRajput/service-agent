from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.tracing import configure_tracing, flush_traces

# Set the LangSmith env vars before anything builds the graph or LLM clients.
TRACING_ENABLED = configure_tracing()

from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.api import chat, health, pricing, slots  # noqa: E402
from app.db import engine  # noqa: E402

UI_DIST = Path(__file__).resolve().parent.parent / "ui" / "dist" / "ui" / "browser"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    if TRACING_ENABLED:
        flush_traces()
    engine.dispose()


app = FastAPI(title="service-agent", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(slots.router)
app.include_router(pricing.router)
app.include_router(chat.router)

if UI_DIST.exists():
    app.mount("/", StaticFiles(directory=UI_DIST, html=True), name="ui")
