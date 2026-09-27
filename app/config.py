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
    llm_provider: Literal["ollama", "openai", "anthropic"] = "openai"
    embedding_provider: Literal["ollama", "openai"] = "ollama"

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"



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
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
