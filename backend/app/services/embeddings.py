"""Embeddings + pgvector retrieval with a portable cosine fallback."""

from __future__ import annotations

import hashlib
import math
import re
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.question import QuestionBank


def _normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def mock_embedding(content: str, dim: int | None = None) -> list[float]:
    """Deterministic hashed bag-of-words embedding (tests/demo, no API key)."""
    dimension = dim or settings.embedding_dim
    vector = [0.0] * dimension
    tokens = re.findall(r"[a-z0-9+#.]{2,}", (content or "").lower())
    if not tokens:
        tokens = ["empty"]
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    return _normalise(vector)


def embed_text(content: str) -> list[float]:
    if settings.llm_provider in {"vertex", "gemini"} and settings.google_cloud_project:
        try:  # pragma: no cover - requires Google credentials
            from app.services.llm.vertex import VertexProvider

            provider = VertexProvider()
            token = provider._access_token()
            import httpx

            url = (
                f"https://{settings.google_cloud_location}-aiplatform.googleapis.com/v1/projects/"
                f"{settings.google_cloud_project}/locations/{settings.google_cloud_location}"
                f"/publishers/google/models/{settings.llm_embedding_model}:predict"
            )
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json={"instances": [{"content": content[:8000]}]},
                timeout=30,
            )
            response.raise_for_status()
            prediction = response.json()["predictions"][0]
            values = prediction.get("embeddings", {}).get("values") or prediction.get("values")
            if values:
                return _normalise([float(v) for v in values])
        except Exception:
            pass
    return mock_embedding(content)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(length))
    norm_a = math.sqrt(sum(v * v for v in a[:length]))
    norm_b = math.sqrt(sum(v * v for v in b[:length]))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_questions(
    db: Session,
    *,
    college_id: uuid.UUID,
    role: str,
    topic: str,
    query: str,
    limit: int = 4,
) -> list[QuestionBank]:
    """Retrieve by role/topic with vector similarity.

    PostgreSQL uses the pgvector `<=>` cosine-distance operator (HNSW index);
    SQLite (tests) ranks in Python. Tenant-owned questions plus global ones only.
    """
    vector = embed_text(query)
    scope = "(college_id = :college_id OR college_id IS NULL)"
    params: dict[str, Any] = {
        "college_id": str(college_id),
        "role": role,
        "topic": topic,
        "limit": limit,
    }
    dialect = db.bind.dialect.name if db.bind is not None else "sqlite"
    if dialect == "postgresql":
        vector_literal = "[" + ",".join(f"{v:.6f}" for v in vector) + "]"
        sql = text(
            f"SELECT id FROM questions WHERE is_active AND {scope} "
            "AND (role = :role OR role = 'general') AND topic = :topic "
            "AND embedding IS NOT NULL "
            "ORDER BY embedding <=> CAST(:vector AS vector) LIMIT :limit"
        )
        params["vector"] = vector_literal
        ids = [row[0] for row in db.execute(sql, params).fetchall()]
        if ids:
            rows = db.query(QuestionBank).filter(QuestionBank.id.in_(ids)).all()
            by_id = {str(r.id): r for r in rows}
            return [by_id[str(i)] for i in ids if str(i) in by_id]
    rows = (
        db.query(QuestionBank)
        .filter(
            QuestionBank.is_active.is_(True),
            (QuestionBank.college_id == college_id) | (QuestionBank.college_id.is_(None)),
            (QuestionBank.role == role) | (QuestionBank.role == "general"),
            QuestionBank.topic == topic,
        )
        .all()
    )
    scored = sorted(
        ((cosine_similarity(vector, q.embedding or []), q) for q in rows),
        key=lambda pair: pair[0],
        reverse=True,
    )
    results = [q for score, q in scored if score > 0][:limit]
    if results:
        return results
    # graceful fallback: any active question in this topic
    return (
        db.query(QuestionBank)
        .filter(
            QuestionBank.is_active.is_(True),
            (QuestionBank.college_id == college_id) | (QuestionBank.college_id.is_(None)),
            QuestionBank.topic == topic,
        )
        .limit(limit)
        .all()
    )
