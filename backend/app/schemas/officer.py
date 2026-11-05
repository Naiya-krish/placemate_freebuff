from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class OfficerKpis(BaseModel):
    total_students: int
    active_30d: int
    resume_uploads: int
    interviews_completed: int
    avg_readiness: int
    placement_date: date | None
    days_to_placement: int | None


class HeatmapCell(BaseModel):
    branch: str
    criterion: str
    value: int
    students: int


class FunnelStage(BaseModel):
    stage: str
    count: int
    percent: int


class WeakSkill(BaseModel):
    skill: str
    gap: int
    students_affected: int


class CohortPoint(BaseModel):
    week: str
    interviews: int
    avg_score: int


class BatchRow(BaseModel):
    branch: str
    students: int
    readiness: int
    interviews: int
    resumes: int


class OfficerStudentRow(BaseModel):
    id: uuid.UUID
    display_name: str
    branch: str | None
    readiness: int | None
    interviews: int
    last_active: str | None
    consent: bool


class OfficerOverview(BaseModel):
    kpis: OfficerKpis
    heatmap: list[HeatmapCell]
    criteria: list[str]
    branches: list[str]
    funnel: list[FunnelStage]
    weakest_skills: list[WeakSkill]
    cohort_progress: list[CohortPoint]
    batch_comparison: list[BatchRow]
    students: list[OfficerStudentRow]
    generated_at: str
    aggregate_only: bool = True
