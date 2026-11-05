from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class RadarPoint(BaseModel):
    key: str
    label: str
    value: int


class BadgeOut(BaseModel):
    key: str
    label: str
    description: str
    earned: bool
    icon: str


class NextAction(BaseModel):
    title: str
    description: str
    href: str
    cta: str
    kind: str


class HistoryItem(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    subtitle: str
    score: int | None
    created_at: datetime


class StudentDashboard(BaseModel):
    readiness: int
    readiness_delta: int
    band: str
    has_resume: bool
    has_interview: bool
    radar: list[RadarPoint]
    streak: int
    xp: int
    level: int
    level_progress: int
    badges: list[BadgeOut]
    next_action: NextAction
    history: list[HistoryItem]
    placement_date: date | None
    days_to_placement: int | None
    resume_score: int | None
    interview_score: int | None
    completed_interviews: int
    total_interviews: int
    skill_gaps: list[str]


class UsageSummary(BaseModel):
    month: str
    tokens: int
    cost_usd: float
    budget_usd: float
    remaining_usd: float
    percent_used: int
