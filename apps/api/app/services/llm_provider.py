from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()


class ProviderConfigurationError(RuntimeError):
    pass


class ModelUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class StreamChunk:
    delta: str
    usage: ModelUsage | None = None


@dataclass
class CompletionResult:
    content: str
    usage: ModelUsage


@dataclass
class ProviderTestResult:
    ok: bool
    status: str
    message: str
    discovered_model_count: int = 0


class OpenAICompatibleProviderAdapter:
    def __init__(self, *, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ProviderConfigurationError("Provider API key is not configured")
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def stream_chat(self, model_name: str, messages: Sequence[dict[str, str]]) -> AsyncIterator[StreamChunk]:
        stream = await self.client.chat.completions.create(
            model=model_name,
            messages=list(messages),
            temperature=0.2,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            usage = None
            if getattr(chunk, "usage", None):
                usage = ModelUsage(
                    prompt_tokens=chunk.usage.prompt_tokens or 0,
                    completion_tokens=chunk.usage.completion_tokens or 0,
                    total_tokens=chunk.usage.total_tokens or 0,
                )
            delta = ""
            if chunk.choices:
                delta = chunk.choices[0].delta.content or ""
            if delta or usage:
                yield StreamChunk(delta=delta, usage=usage)

    async def complete_chat(self, model_name: str, messages: Sequence[dict[str, str]]) -> CompletionResult:
        content = ""
        usage = ModelUsage()
        async for chunk in self.stream_chat(model_name, messages):
            content += chunk.delta
            if chunk.usage is not None:
                usage = chunk.usage
        return CompletionResult(content=content, usage=usage)

    async def embed_texts(
        self,
        texts: Sequence[str],
        model_name: str,
        *,
        input_type: str | None = None,
    ) -> list[list[float]]:
        request_attempts: list[dict] = []
        base_attempt: dict = {}
        if settings.OPENAI_EMBEDDING_DIMENSIONS:
            base_attempt["dimensions"] = settings.OPENAI_EMBEDDING_DIMENSIONS
        if input_type:
            base_attempt["extra_body"] = {"input_type": input_type}

        request_attempts.append(base_attempt.copy())
        if "dimensions" in base_attempt:
            attempt = base_attempt.copy()
            attempt.pop("dimensions", None)
            request_attempts.append(attempt)
        if "extra_body" in base_attempt:
            attempt = base_attempt.copy()
            attempt.pop("extra_body", None)
            request_attempts.append(attempt)
        if "dimensions" in base_attempt and "extra_body" in base_attempt:
            request_attempts.append({})

        if not request_attempts:
            request_attempts.append({})

        seen_attempts: set[tuple[tuple[str, str], ...]] = set()
        last_error: Exception | None = None

        for optional_args in request_attempts:
            fingerprint = tuple(sorted((key, str(value)) for key, value in optional_args.items()))
            if fingerprint in seen_attempts:
                continue
            seen_attempts.add(fingerprint)
            try:
                response = await self.client.embeddings.create(
                    model=model_name,
                    input=list(texts),
                    **optional_args,
                )
                return [list(item.embedding) for item in response.data]
            except Exception as exc:
                last_error = exc

        if last_error is None:
            raise RuntimeError("Embedding request failed before any provider attempt was made.")
        raise last_error

    async def list_models(self) -> list[dict]:
        response = await self.client.models.list()
        models: list[dict] = []
        for item in response.data:
            model_name = getattr(item, "id", None) or getattr(item, "name", None)
            if not model_name:
                continue
            lowered = str(model_name).lower()
            kind = "embedding" if "embed" in lowered or "embedding" in lowered else "chat"
            models.append(
                {
                    "name": model_name,
                    "kind": kind,
                    "source": "discovered",
                    "metadata": {"owned_by": getattr(item, "owned_by", None)},
                }
            )
        return sorted(models, key=lambda item: (item["kind"], item["name"]))

    async def test_connection(self) -> ProviderTestResult:
        try:
            models = await self.list_models()
            return ProviderTestResult(
                ok=True,
                status="active",
                message="Connection is valid and model discovery succeeded.",
                discovered_model_count=len(models),
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            message = str(exc)
            if status_code in {404, 405} or "404" in message or "405" in message:
                return ProviderTestResult(
                    ok=True,
                    status="manual_entry_required",
                    message="Connection is reachable but model discovery is unavailable. Add model names manually.",
                    discovered_model_count=0,
                )
            raise


OpenAIProviderAdapter = OpenAICompatibleProviderAdapter
