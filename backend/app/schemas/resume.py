from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ResumeOut(ORMModel):
    id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    used_ocr: bool
    pages: int
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


class ResumeDetail(ResumeOut):
    raw_text: str
    parsed_data: dict[str, Any]


class AnalysisRequest(BaseModel):
    job_description: str = Field(default="", max_length=6000)
    target_role: str | None = Field(default=None, max_length=80)


class SuggestionOut(BaseModel):
    id: str
    category: str
    target_section: str
    original: str
    improved: str
    rationale: str
    supported: bool = True
    decision: Literal["pending", "accepted", "rejected"] = "pending"


class MissingEvidenceOut(BaseModel):
    item: str
    reason: str


class AnalysisOut(ORMModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    target_role: str
    job_description: str
    score: int
    subscores: dict[str, int]
    suggestions: list[dict[str, Any]]
    missing_evidence: list[dict[str, Any]]
    injection_flags: list[str]
    prompt_version: str
    model: str
    created_at: datetime


class SuggestionDecision(BaseModel):
    accept: bool


class AnalysisSummary(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    target_role: str
    score: int
    created_at: datetime
