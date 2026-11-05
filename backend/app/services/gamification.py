"""Streaks, XP, levels and badges."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.interview import Interview
from app.models.resume import ResumeAnalysis
from app.models.user import User
from app.schemas.dashboard import BadgeOut

XP_PER_LEVEL = 250


def touch_streak(user: User, today: date | None = None) -> None:
    today = today or date.today()
    if user.last_active_date == today:
        return
    if user.last_active_date == today - timedelta(days=1):
        user.streak_count = max(1, user.streak_count + 1)
    else:
        user.streak_count = 1
    user.last_active_date = today


def award_xp(user: User, amount: int) -> None:
    user.xp = max(0, user.xp + amount)


def level_for(xp: int) -> int:
    return xp // XP_PER_LEVEL + 1


def level_progress(xp: int) -> int:
    return int((xp % XP_PER_LEVEL) / XP_PER_LEVEL * 100)


def badge_catalogue(
    db: Session,
    user: User,
    *,
    resume_score: int | None,
    readiness: int,
) -> list[BadgeOut]:
    interviews: int = (
        db.query(func.count(Interview.id))
        .filter(Interview.user_id == user.id, Interview.status == "completed")
        .scalar()
        or 0
    )
    resumes = (
        db.query(func.count(ResumeAnalysis.id)).filter(ResumeAnalysis.user_id == user.id).count()
    )
    return [
        BadgeOut(
            key="first_resume",
            label="First impression",
            description="Uploaded and scored your first resume",
            earned=resumes > 0,
            icon="file",
        ),
        BadgeOut(
            key="first_interview",
            label="In the hot seat",
            description="Completed your first mock interview",
            earned=interviews >= 1,
            icon="mic",
        ),
        BadgeOut(
            key="three_interviews",
            label="Interview athlete",
            description="Completed three mock interviews",
            earned=interviews >= 3,
            icon="trophy",
        ),
        BadgeOut(
            key="resume_80",
            label="Resume sharpener",
            description="Scored 80+ on a resume analysis",
            earned=(resume_score or 0) >= 80,
            icon="sparkles",
        ),
        BadgeOut(
            key="streak_3",
            label="On a roll",
            description="Practised three days in a row",
            earned=user.streak_count >= 3,
            icon="flame",
        ),
        BadgeOut(
            key="ready_70",
            label="Placement ready",
            description="Reached a readiness score of 70",
            earned=readiness >= 70,
            icon="shield",
        ),
        BadgeOut(
            key="xp_500",
            label="500 club",
            description="Earned 500 XP",
            earned=user.xp >= 500,
            icon="zap",
        ),
    ]


def placeholder_user_id() -> uuid.UUID:
    return uuid.uuid4()
