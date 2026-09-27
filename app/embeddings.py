from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from langfuse.openai import OpenAI

from app.config import get_settings

DIMENSIONS = {
    "nomic-embed-text": 768,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


def dimensions_of(model: str) -> int:
    if model not in DIMENSIONS:
        raise RuntimeError(f"unknown embedding model {model!r}: add its dimension to DIMENSIONS")
    return DIMENSIONS[model]


class Embedder(Protocol):
    model: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class OpenAICompatibleEmbedder:
    client: OpenAI
    model: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()

    if settings.embedding_provider == "ollama":
        client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")
        model = settings.ollama_embedding_model
    else:
        if not settings.openai_api_key:
            raise RuntimeError("EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is empty")
        client = OpenAI(api_key=settings.openai_api_key)
        model = settings.openai_embedding_model

    return OpenAICompatibleEmbedder(client, model, dimensions_of(model))
