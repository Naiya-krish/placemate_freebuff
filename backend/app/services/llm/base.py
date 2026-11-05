from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    provider: str
    latency_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMProvider(Protocol):
    name: str

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        task: str = "",
        variables: dict[str, Any] | None = None,
    ) -> LLMResult: ...


class LLMProviderError(RuntimeError):
    """Upstream provider failure (safe to retry / surface as 502)."""
