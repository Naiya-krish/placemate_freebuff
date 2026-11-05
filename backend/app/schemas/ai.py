"""Strict contracts for every AI response. Invalid output is retried, then rejected."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ExperienceItem(StrictModel):
    company: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=200)
    start: str = Field(default="", max_length=40)
    end: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=120)
    bullets: list[str] = Field(default_factory=list, max_length=12)


class ProjectItem(StrictModel):
    name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=1600)
    tech: list[str] = Field(default_factory=list, max_length=20)
    bullets: list[str] = Field(default_factory=list, max_length=12)


class EducationItem(StrictModel):
    institution: str = Field(default="", max_length=200)
    degree: str = Field(default="", max_length=160)
    field: str = Field(default="", max_length=160)
    start: str = Field(default="", max_length=40)
    end: str = Field(default="", max_length=40)
    score: str = Field(default="", max_length=40)


class ResumeParseAI(StrictModel):
    full_name: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=40)
    links: list[str] = Field(default_factory=list, max_length=10)
    summary: str = Field(default="", max_length=1200)
    skills: list[str] = Field(default_factory=list, max_length=80)
    experience: list[ExperienceItem] = Field(default_factory=list, max_length=20)
    projects: list[ProjectItem] = Field(default_factory=list, max_length=20)
    education: list[EducationItem] = Field(default_factory=list, max_length=10)
    certifications: list[str] = Field(default_factory=list, max_length=20)
    achievements: list[str] = Field(default_factory=list, max_length=20)


class Subscores(StrictModel):
    clarity: int = Field(ge=0, le=100)
    impact: int = Field(ge=0, le=100)
    relevance: int = Field(ge=0, le=100)
    structure: int = Field(ge=0, le=100)
    keywords: int = Field(ge=0, le=100)


class SuggestionAI(StrictModel):
    target_section: str = Field(default="experience", max_length=60)
    category: str = Field(default="impact", max_length=40)
    original: str = Field(min_length=1, max_length=1200)
    improved: str = Field(min_length=1, max_length=1500)
    rationale: str = Field(min_length=1, max_length=500)


class MissingEvidenceAI(StrictModel):
    item: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=300)


class AnalysisAI(StrictModel):
    overall_score: int = Field(ge=0, le=100)
    subscores: Subscores
    suggestions: list[SuggestionAI] = Field(default_factory=list, max_length=10)
    missing_evidence: list[MissingEvidenceAI] = Field(default_factory=list, max_length=15)
    summary: str = Field(default="", max_length=1200)

    @model_validator(mode="after")
    def at_least_one_signal(self) -> AnalysisAI:
        if not self.suggestions and not self.missing_evidence and not self.summary:
            raise ValueError("analysis must contain at least one suggestion, gap or summary")
        return self


class InterviewQuestionAI(StrictModel):
    question: str = Field(min_length=8, max_length=600)
    intent: str = Field(default="assess depth", max_length=200)
    difficulty: str = Field(default="medium", max_length=20)

    @field_validator("difficulty")
    @classmethod
    def valid_difficulty(cls, value: str) -> str:
        return value if value in {"easy", "medium", "hard"} else "medium"


class CriterionScoreAI(StrictModel):
    key: str = Field(min_length=2, max_length=40)
    score: int = Field(ge=0, le=10)
    note: str = Field(min_length=3, max_length=600)
    improvement: str = Field(min_length=3, max_length=400)


class RubricScoreAI(StrictModel):
    criteria: list[CriterionScoreAI] = Field(min_length=1, max_length=8)
    strengths: list[str] = Field(default_factory=list, max_length=6)
    improvements: list[str] = Field(default_factory=list, max_length=6)
    summary: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def unique_criteria(self) -> RubricScoreAI:
        keys = [c.key for c in self.criteria]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate rubric criterion keys")
        return self
