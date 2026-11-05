"""Student dashboard and personal AI usage budget."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, get_college
from app.models.enums import Role
from app.schemas.dashboard import StudentDashboard, UsageSummary
from app.services import gamification
from app.services.cost import usage_summary
from app.services.dashboard import build_student_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/student", response_model=StudentDashboard)
def student_dashboard(user: CurrentUser, db: DbSession) -> StudentDashboard:
    from app.core.errors import ForbiddenError

    if user.role != Role.STUDENT.value:
        raise ForbiddenError("Student dashboard is available to student accounts only")
    college = get_college(db, user)
    gamification.touch_streak(user)
    db.commit()
    return build_student_dashboard(db, user, college)


@router.get("/usage/me", response_model=UsageSummary)
def my_usage(user: CurrentUser, db: DbSession) -> UsageSummary:
    return usage_summary(db, user)
