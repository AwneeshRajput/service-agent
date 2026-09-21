from fastapi import FastAPI
from sqlalchemy import create_engine, text

from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)

app = FastAPI(title="service-agent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"

    return {"status": "ok", "env": settings.app_env, "database": database}
