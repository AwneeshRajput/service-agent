from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    engine.dispose()


app = FastAPI(title="service-agent", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
