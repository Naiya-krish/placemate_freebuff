"""Vertex AI Gemini provider over the REST API (no heavy SDK dependency)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import LLMMessage, LLMProviderError, LLMResult


class VertexProvider:
    name = "vertex"

    def __init__(self) -> None:
        self.project = settings.google_cloud_project
        self.location = settings.google_cloud_location
        self._credentials: Any = None

    def _access_token(self) -> str:
        if self._credentials is None:
            try:
                import google.auth
                from google.auth.transport.requests import Request as GoogleRequest
            except ImportError as exc:  # pragma: no cover - optional dependency path
                raise LLMProviderError(
                    "google-auth is required for Vertex AI. Install google-auth or use LLM_PROVIDER=mock."
                ) from exc
            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            self._credentials, detected_project = google.auth.default(scopes=scopes)
            if not self.project:
                self.project = detected_project
            self._credentials.refresh(GoogleRequest())
        return str(self._credentials.token)

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
        if not self.project:
            raise LLMProviderError("GOOGLE_CLOUD_PROJECT is required for Vertex AI")
        started = time.perf_counter()
        system_parts = [m.content for m in messages if m.role == "system"]
        contents = [
            {"role": "user", "parts": [{"text": m.content}]} for m in messages if m.role != "system"
        ]
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        url = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project}"
            f"/locations/{self.location}/publishers/google/models/{model}:generateContent"
        )
        try:
            response = httpx.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {self._access_token()}"},
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Vertex AI request failed: {exc}") from exc

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError("Vertex AI returned no candidate text") from exc
        usage = data.get("usageMetadata", {})
        return LLMResult(
            text=text,
            model=model,
            input_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0)),
            provider=self.name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            raw={"safetyRatings": data["candidates"][0].get("safetyRatings", [])},
        )
