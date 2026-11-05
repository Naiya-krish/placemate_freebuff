"""Versioned prompt registry. Prompts are files, never string literals in routes."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = PROMPTS_DIR / "manifest.json"


class PromptNotFoundError(KeyError):
    pass


@dataclass(frozen=True)
class PromptSpec:
    id: str
    version: str
    path: Path
    tier: str
    temperature: float
    max_tokens: int
    checksum: str
    body: str


@lru_cache
def load_prompts() -> dict[str, PromptSpec]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    specs: dict[str, PromptSpec] = {}
    for prompt_id, meta in manifest["prompts"].items():
        path = PROMPTS_DIR / meta["file"]
        body = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        specs[prompt_id] = PromptSpec(
            id=prompt_id,
            version=meta["version"],
            path=path,
            tier=meta["tier"],
            temperature=float(meta["temperature"]),
            max_tokens=int(meta["max_tokens"]),
            checksum=checksum,
            body=body,
        )
    return specs


def get_prompt(prompt_id: str) -> PromptSpec:
    try:
        return load_prompts()[prompt_id]
    except KeyError as exc:
        raise PromptNotFoundError(prompt_id) from exc


def prompt_version(prompt_id: str) -> str:
    return get_prompt(prompt_id).version


def render_prompt(prompt_id: str, **variables: Any) -> str:
    """Replace ``{{name}}`` placeholders without evaluating untrusted content."""

    spec = get_prompt(prompt_id)
    rendered = spec.body
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    unresolved = sorted(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", rendered)))
    if unresolved:
        raise ValueError(f"unresolved prompt variables: {unresolved}")
    return rendered


def prompt_manifest() -> dict[str, Any]:
    return {
        prompt_id: {
            "version": spec.version,
            "checksum": spec.checksum,
            "tier": spec.tier,
            "temperature": spec.temperature,
            "file": str(spec.path.relative_to(PROMPTS_DIR)),
        }
        for prompt_id, spec in load_prompts().items()
    }
