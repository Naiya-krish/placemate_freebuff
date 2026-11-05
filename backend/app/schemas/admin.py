from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CollegeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=32)
    city: str | None = Field(default=None, max_length=120)
    placement_date: date | None = None


class CollegeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    city: str | None = Field(default=None, max_length=120)
    placement_date: date | None = None
    is_active: bool | None = None


class CollegeOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    city: str | None
    placement_date: date | None
    is_active: bool
    created_at: datetime
    student_count: int = 0


class QuestionCreate(BaseModel):
    prompt: str = Field(min_length=8, max_length=1200)
    ideal_answer: str = Field(default="", max_length=2000)
    role: str = Field(default="swe", max_length=40)
    topic: str = Field(default="project", max_length=40)
    difficulty: str = Field(default="medium", max_length=16)
    key_points: list[str] = Field(default_factory=list, max_length=12)
    is_global: bool = False


class QuestionUpdate(BaseModel):
    prompt: str | None = Field(default=None, min_length=8, max_length=1200)
    ideal_answer: str | None = Field(default=None, max_length=2000)
    role: str | None = Field(default=None, max_length=40)
    topic: str | None = Field(default=None, max_length=40)
    difficulty: str | None = Field(default=None, max_length=16)
    key_points: list[str] | None = Field(default=None, max_length=12)
    is_active: bool | None = None


class QuestionOut(ORMModel):
    id: uuid.UUID
    college_id: uuid.UUID | None
    prompt: str
    ideal_answer: str
    role: str
    topic: str
    difficulty: str
    key_points: list[str]
    is_active: bool
    created_at: datetime


class CriterionCreate(BaseModel):
    key: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=80)
    weight: float = Field(gt=0, le=1)
    description: str = Field(min_length=5, max_length=400)


class RubricCreate(BaseModel):
    version: str = Field(min_length=1, max_length=32)
    label: str = Field(default="Custom rubric", max_length=120)
    criteria: list[CriterionCreate] = Field(min_length=1, max_length=8)
    activate: bool = True


class RubricOut(ORMModel):
    id: uuid.UUID
    version: str
    label: str
    criteria: list[dict[str, Any]]
    is_active: bool
    created_at: datetime


class AdminUsageRow(BaseModel):
    college_id: uuid.UUID
    college_name: str
    month: str
    tokens: int
    cost_usd: float
    users_billable: int


class AdminOverview(BaseModel):
    colleges: int
    students: int
    interviews: int
    usage: list[AdminUsageRow]
