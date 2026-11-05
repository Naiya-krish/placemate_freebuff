"""Admin console: colleges, question bank, rubric versions and usage."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func

from app.api.deps import DbSession, Repo, require_roles
from app.core.errors import ApiError, NotFoundError
from app.models.enums import Role
from app.models.interview import Interview
from app.models.question import QuestionBank
from app.models.rubric import RubricVersion
from app.models.usage import UsageEvent
from app.models.user import College, User
from app.schemas.admin import (
    AdminOverview,
    AdminUsageRow,
    CollegeCreate,
    CollegeOut,
    CollegeUpdate,
    QuestionCreate,
    QuestionOut,
    QuestionUpdate,
    RubricCreate,
    RubricOut,
)
from app.services.defaults import ensure_default_rubric
from app.services.embeddings import embed_text

router = APIRouter(prefix="/admin", tags=["admin"])
AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]


@router.get("/overview", response_model=AdminOverview)
def admin_overview(user: AdminUser, db: DbSession) -> AdminOverview:
    rows = (
        db.query(
            UsageEvent.college_id,
            College.name,
            UsageEvent.month,
            func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens).label("tokens"),
            func.sum(UsageEvent.cost_usd).label("cost"),
            func.count(func.distinct(UsageEvent.user_id)).label("users"),
        )
        .join(College, College.id == UsageEvent.college_id)
        .group_by(UsageEvent.college_id, College.name, UsageEvent.month)
        .order_by(UsageEvent.month.desc())
        .all()
    )
    usage = [
        AdminUsageRow(
            college_id=row[0],
            college_name=row[1],
            month=row[2],
            tokens=int(row[3] or 0),
            cost_usd=round(float(row[4] or 0), 4),
            users_billable=int(row[5] or 0),
        )
        for row in rows
    ]
    return AdminOverview(
        colleges=db.query(College).count(),
        students=db.query(User).filter(User.role == Role.STUDENT.value).count(),
        interviews=db.query(Interview).filter(Interview.status == "completed").count(),
        usage=usage,
    )


@router.get("/colleges", response_model=list[CollegeOut])
def list_colleges(db: DbSession) -> list[CollegeOut]:
    counts: dict[uuid.UUID, int] = {
        row[0]: int(row[1])
        for row in db.query(User.college_id, func.count(User.id))
        .filter(User.role == Role.STUDENT.value)
        .group_by(User.college_id)
        .all()
    }
    colleges = db.query(College).order_by(College.created_at.desc()).all()
    out = []
    for college in colleges:
        row = CollegeOut.model_validate(college)
        row.student_count = int(counts.get(college.id, 0))
        out.append(row)
    return out


@router.post("/colleges", response_model=CollegeOut, status_code=201)
def create_college(payload: CollegeCreate, db: DbSession) -> College:
    code = payload.code.strip().upper()
    if db.query(College).filter(func.upper(College.code) == code).first():
        raise ApiError(409, "A college with that code already exists", "college_exists")
    college = College(
        name=payload.name.strip(),
        code=code,
        city=payload.city,
        placement_date=payload.placement_date,
    )
    db.add(college)
    db.flush()
    ensure_default_rubric(db, college.id)
    db.commit()
    db.refresh(college)
    return college


@router.patch("/colleges/{college_id}", response_model=CollegeOut)
def update_college(college_id: uuid.UUID, payload: CollegeUpdate, db: DbSession) -> College:
    college = db.get(College, college_id)
    if college is None:
        raise NotFoundError("College not found")
    for field in ("name", "city", "placement_date", "is_active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(college, field, value)
    db.commit()
    db.refresh(college)
    return college


@router.get("/questions", response_model=list[QuestionOut])
def list_questions(
    db: DbSession, role: str | None = None, topic: str | None = None
) -> list[QuestionBank]:
    query = db.query(QuestionBank)
    if role:
        query = query.filter(QuestionBank.role == role)
    if topic:
        query = query.filter(QuestionBank.topic == topic)
    return query.order_by(QuestionBank.created_at.desc()).limit(200).all()


@router.post("/questions", response_model=QuestionOut, status_code=201)
def create_question(payload: QuestionCreate, repo: Repo, db: DbSession) -> QuestionBank:
    question = QuestionBank(
        college_id=None if payload.is_global else repo.college_id,
        role=payload.role,
        topic=payload.topic,
        difficulty=payload.difficulty,
        prompt=payload.prompt.strip(),
        ideal_answer=payload.ideal_answer.strip(),
        key_points=payload.key_points,
        embedding=embed_text(payload.prompt + " " + " ".join(payload.key_points)),
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.patch("/questions/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: uuid.UUID, payload: QuestionUpdate, repo: Repo, db: DbSession
) -> QuestionBank:
    question = repo.get_or_404(QuestionBank, question_id, "Question not found")
    for field in (
        "prompt",
        "ideal_answer",
        "role",
        "topic",
        "difficulty",
        "key_points",
        "is_active",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(question, field, value)
    if payload.prompt is not None:
        question.embedding = embed_text(question.prompt + " " + " ".join(question.key_points or []))
    db.commit()
    db.refresh(question)
    return question


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: uuid.UUID, repo: Repo, db: DbSession) -> Response:
    question = repo.get_or_404(QuestionBank, question_id, "Question not found")
    question.is_active = False
    db.commit()
    return Response(status_code=204)


@router.get("/rubrics", response_model=list[RubricOut])
def list_rubrics(repo: Repo) -> list[RubricVersion]:
    return repo.query(RubricVersion).order_by(RubricVersion.created_at.desc()).all()


@router.post("/rubrics", response_model=RubricOut, status_code=201)
def create_rubric(payload: RubricCreate, repo: Repo, db: DbSession) -> RubricVersion:
    keys = [c.key for c in payload.criteria]
    if len(keys) != len(set(keys)):
        raise ApiError(422, "Rubric criterion keys must be unique", "invalid_rubric")
    total = round(sum(c.weight for c in payload.criteria), 3)
    if abs(total - 1.0) > 0.01:
        raise ApiError(422, f"Criterion weights must sum to 1.0 (got {total})", "invalid_rubric")
    if repo.query(RubricVersion).filter(RubricVersion.version == payload.version).first():
        raise ApiError(409, "That rubric version already exists", "rubric_exists")
    if payload.activate:
        repo.query(RubricVersion).update({"is_active": False})
    rubric = RubricVersion(
        college_id=repo.college_id,
        version=payload.version.strip(),
        label=payload.label.strip(),
        criteria=[c.model_dump() for c in payload.criteria],
        is_active=payload.activate,
    )
    repo.add(rubric)
    db.commit()
    db.refresh(rubric)
    return rubric


@router.post("/rubrics/{rubric_id}/activate", response_model=RubricOut)
def activate_rubric(rubric_id: uuid.UUID, repo: Repo, db: DbSession) -> RubricVersion:
    rubric = repo.get_or_404(RubricVersion, rubric_id, "Rubric not found")
    repo.query(RubricVersion).update({"is_active": False})
    rubric.is_active = True
    db.commit()
    db.refresh(rubric)
    return rubric
