from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import InterviewStatus, Round, Speaker
from app.schemas.common import ORMModel


class InterviewCreate(BaseModel):
    resume_id: uuid.UUID
    role: str = Field(default="swe", max_length=40)
    target_role: str | None = Field(default=None, max_length=80)


class RubricCriterionOut(BaseModel):
    key: str
    label: str
    weight: float
    description: str


class RubricOut(BaseModel):
    version: str
    label: str
    criteria: list[RubricCriterionOut]


class TurnOut(ORMModel):
    id: uuid.UUID
    idx: int
    round: Round
    speaker: Speaker
    content: str
    is_followup: bool
    hint_used: bool
    created_at: datetime


class ScoreCriterionOut(BaseModel):
    key: str
    label: str
    weight: float
    score: int
    note: str
    improvement: str


class InterviewOut(ORMModel):
    id: uuid.UUID
    resume_id: uuid.UUID | None
    role: str
    status: InterviewStatus
    current_round: Round
    rubric_version: str
    prompt_version: str
    model: str
    overall_score: float | None
    duration_seconds: int
    hint_count: int
    variance_flag: bool
    needs_review: bool
    started_at: datetime
    completed_at: datetime | None


class InterviewDetail(InterviewOut):
    rubric_scores: list[dict[str, Any]]
    feedback: dict[str, Any]
    turns: list[TurnOut]


class FeedbackOut(BaseModel):
    interview_id: uuid.UUID
    overall_score: float | None
    rubric_version: str
    criteria: list[ScoreCriterionOut]
    feedback: dict[str, Any]
    transcript: list[TurnOut]
    variance_flag: bool


class AnswerIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
