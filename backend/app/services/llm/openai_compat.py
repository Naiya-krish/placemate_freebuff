"""OpenAI-compatible chat-completions provider (OpenAI, Groq, Together, Ollama…)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import LLMMessage, LLMProviderError, LLMResult


class OpenAICompatibleProvider:
    name = "openai"

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        task: str = "",
        variables: dict[str, Any] | None = None,
    ) -> LLMResult:
        if not settings.llm_api_key:
            raise LLMProviderError("LLM_API_KEY is required for the OpenAI-compatible provider")
        started = time.perf_counter()
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            response = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"LLM request failed: {exc}") from exc
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError("LLM returned no message content") from exc
        usage = data.get("usage", {})
        return LLMResult(
            text=text,
            model=model,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            provider=self.name,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
