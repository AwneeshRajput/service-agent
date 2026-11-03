from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # "require" for hosted Postgres like Neon; "prefer" also works with the local Docker DB (no SSL).
    postgres_sslmode: Literal["disable", "prefer", "require", "verify-ca", "verify-full"] = "prefer"
    llm_provider: Literal["ollama", "openai", "anthropic"] = "openai"
    # Must match how manual_chunks was ingested (python -m app.rag.ingest); openai = 1536 dims.
    embedding_provider: Literal["ollama", "openai"] = "openai"

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    # LangSmith tracing: on only when LANGSMITH_TRACING=true and an API key is set.
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "service-agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"


    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    openai_fast_model: str = "gpt-5.4-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?sslmode={self.postgres_sslmode}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
