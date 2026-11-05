"""Officer analytics: aggregate-only cohort readiness and PDF export."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import DbSession, get_college, require_roles
from app.models.enums import Role
from app.models.user import User
from app.schemas.officer import OfficerOverview
from app.services.analytics import overview as build_overview
from app.services.report import build_overview_pdf

router = APIRouter(prefix="/officer", tags=["officer"])

OfficerUser = Annotated[User, Depends(require_roles(Role.OFFICER, Role.ADMIN))]


@router.get("/overview", response_model=OfficerOverview)
def overview(user: OfficerUser, db: DbSession) -> OfficerOverview:
    college = get_college(db, user)
    return build_overview(db, college)


@router.get(
    "/report.pdf",
    responses={200: {"content": {"application/pdf": {}}}},
    status_code=status.HTTP_200_OK,
)
def report(user: OfficerUser, db: DbSession) -> Response:
    college = get_college(db, user)
    data = build_overview(db, college)
    pdf = build_overview_pdf(data, college.name)
    filename = f"placemate-{college.code.lower()}-readiness.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
