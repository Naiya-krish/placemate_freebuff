from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    STUDENT = "student"
    OFFICER = "officer"
    ADMIN = "admin"


class ResumeStatus(str, Enum):
    PARSED = "parsed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class InterviewStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Round(str, Enum):
    PROJECT = "project"
    TECHNICAL = "technical"
    HR = "hr"


class Speaker(str, Enum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    SYSTEM = "system"


ROUND_ORDER: list[Round] = [Round.PROJECT, Round.TECHNICAL, Round.HR]
ROUND_TITLES: dict[str, str] = {
    Round.PROJECT.value: "Project deep-dive",
    Round.TECHNICAL.value: "Technical basics",
    Round.HR.value: "HR & behavioural",
}
