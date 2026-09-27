import asyncio
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol, TypeVar

from langfuse.openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)

class LLM(Protocol):
    model: str

    def complete(self, system: str, user: str) -> str: ...


@dataclass
class OpenAICompatibleLLM:
    client: OpenAI
    model: str

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


@dataclass
class AnthropicLLM:
    client: Any
    model: str

    def complete(self, system: str, user: str) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in message.content if block.type == "text")

# Caches the initialized client instance in memory -
# so it doesn't re-read settings or re-create API client -
# connections on every request.
@lru_cache
def get_llm() -> LLM:
    settings = get_settings()

    if settings.llm_provider == "ollama":
        client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama", timeout=60.0, max_retries=2)
        return OpenAICompatibleLLM(client, settings.ollama_model)

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is empty")
        client = OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=2)
        return OpenAICompatibleLLM(client, settings.openai_model)

    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError("LLM_PROVIDER=anthropic needs: pip install anthropic") from e
    if not settings.anthropic_api_key:
        raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty")
    client = Anthropic(api_key=settings.anthropic_api_key, timeout=30.0, max_retries=2)
    return AnthropicLLM(client, settings.anthropic_model)

class LLMOutputError(Exception):
    pass


def _json_part(raw: str) -> str:
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start : end + 1] if 0 <= start < end else raw


def complete_structured(system: str, user: str, schema: type[T], retries: int = 2) -> T:
    llm = get_llm()
    system = (
        f"{system}\n\nReply with ONE JSON object that matches this JSON schema. "
        f"No prose, no code fences.\n{json.dumps(schema.model_json_schema())}"
    )
    prompt = user
    last_error = ""
    for _ in range(retries + 1):
        raw = llm.complete(system, prompt)
        try:
            return schema.model_validate_json(_json_part(raw))
        except ValidationError as error:
            last_error = str(error)[:500]
            prompt = f"{user}\n\nYour previous reply was invalid:\n{last_error}\nReply again with valid JSON only."
    raise LLMOutputError(f"no valid {schema.__name__} after {retries + 1} attempts: {last_error}")


async def acomplete_structured(system: str, user: str, schema: type[T], retries: int = 2) -> T:
    return await asyncio.to_thread(complete_structured, system, user, schema, retries)
