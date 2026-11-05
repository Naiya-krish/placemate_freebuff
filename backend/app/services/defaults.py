"""Default rubric, role mappings and shared constants."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.rubric import RubricVersion

DEFAULT_RUBRIC_VERSION = "v1"
DEFAULT_RUBRIC_LABEL = "PlaceMate standard rubric v1"

DEFAULT_CRITERIA: list[dict[str, object]] = [
    {
        "key": "clarity",
        "label": "Clarity",
        "weight": 0.18,
        "description": "Answers are structured, concise and easy to follow; claims are understandable without jargon.",
    },
    {
        "key": "technical_depth",
        "label": "Technical depth",
        "weight": 0.24,
        "description": "Explains mechanisms, constraints and trade-offs at the right level for the target role.",
    },
    {
        "key": "problem_solving",
        "label": "Problem solving",
        "weight": 0.22,
        "description": "Shows a reasoned approach, considers alternatives and validates the outcome with evidence.",
    },
    {
        "key": "communication",
        "label": "Communication",
        "weight": 0.16,
        "description": "Listens, answers the question asked and adapts explanations to the interviewer.",
    },
    {
        "key": "role_fit",
        "label": "Role fit",
        "weight": 0.20,
        "description": "Examples and motivations match the target role and its expected responsibilities.",
    },
]

ROLE_CODE_MAP = {
    "software engineer": "swe",
    "sde": "swe",
    "backend": "swe",
    "frontend": "swe",
    "full stack": "swe",
    "data analyst": "data",
    "data scientist": "data",
    "data engineer": "data",
    "machine learning": "data",
    "product manager": "product",
    "product": "product",
    "core electronics": "core",
    "vlsi": "core",
    "embedded": "core",
}


def role_code(target_role: str | None) -> str:
    if not target_role:
        return "swe"
    lowered = target_role.lower()
    for key, code in ROLE_CODE_MAP.items():
        if key in lowered:
            return code
    return "swe"


def ensure_default_rubric(db: Session, college_id: uuid.UUID) -> RubricVersion:
    existing = (
        db.query(RubricVersion)
        .filter(RubricVersion.college_id == college_id, RubricVersion.is_active.is_(True))
        .order_by(RubricVersion.created_at.desc())
        .first()
    )
    if existing:
        return existing
    rubric = RubricVersion(
        college_id=college_id,
        version=DEFAULT_RUBRIC_VERSION,
        label=DEFAULT_RUBRIC_LABEL,
        criteria=DEFAULT_CRITERIA,
        is_active=True,
    )
    db.add(rubric)
    db.flush()
    return rubric


def active_rubric(db: Session, college_id: uuid.UUID) -> RubricVersion:
    return ensure_default_rubric(db, college_id)


def rubric_weights(criteria: list[dict[str, object]]) -> dict[str, float]:
    weights = {str(c["key"]): float(str(c["weight"])) for c in criteria}
    total = sum(weights.values()) or 1.0
    return {key: weight / total for key, weight in weights.items()}
