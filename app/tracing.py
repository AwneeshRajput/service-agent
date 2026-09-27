from functools import lru_cache

from langfuse import Langfuse

from app.config import get_settings


@lru_cache
def get_tracer() -> Langfuse | None:
    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
        environment=settings.app_env,
    )