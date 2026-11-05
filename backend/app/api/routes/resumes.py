"""Resume upload, detail, analysis and accept/reject decisions."""

import uuid

from fastapi import APIRouter, File, Request, Response, UploadFile

from app.api.deps import CurrentUser, DbSession, Repo
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.ratelimit import limiter
from app.models.enums import Role
from app.models.resume import Resume, ResumeAnalysis
from app.models.user import User
from app.schemas.resume import (
    AnalysisOut,
    AnalysisRequest,
    ResumeDetail,
    ResumeOut,
    SuggestionDecision,
)
from app.services.resume_parser import PayloadTooLargeError
from app.services.resume_service import (
    analyze_resume,
    create_resume,
    set_suggestion_decision,
)
from app.services.storage import get_storage

router = APIRouter(tags=["resumes"])


def _owned_resume(repo: Repo, user: User, resume_id: uuid.UUID) -> Resume:
    resume = repo.get_or_404(Resume, resume_id, "Resume not found")
    if resume.user_id != user.id:
        raise NotFoundError("Resume not found")
    return resume


@router.post("/resumes", response_model=ResumeDetail, status_code=201)
@limiter.limit(settings.rate_limit_upload)
def upload_resume(
    request: Request,
    user: CurrentUser,
    response: Response,
    db: DbSession,
    repo: Repo,
    file: UploadFile = File(...),
) -> Resume:
    if user.role != Role.STUDENT.value:
        from app.core.errors import ForbiddenError

        raise ForbiddenError("Only students can upload resumes")
    payload = file.file.read(settings.max_upload_bytes + 1)
    if len(payload) > settings.max_upload_bytes:
        raise PayloadTooLargeError()
    resume = create_resume(
        db,
        repo,
        user,
        filename=file.filename or "resume",
        content_type=file.content_type,
        data=payload,
    )
    db.commit()
    db.refresh(resume)
    response.status_code = 201
    return resume


@router.get("/resumes", response_model=list[ResumeOut])
def list_resumes(user: CurrentUser, db: DbSession, repo: Repo) -> list[Resume]:
    if user.role != Role.STUDENT.value:
        return []
    return (
        repo.query(Resume)
        .filter(Resume.user_id == user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )


@router.get("/resumes/{resume_id}", response_model=ResumeDetail)
def get_resume(resume_id: uuid.UUID, user: CurrentUser, repo: Repo) -> Resume:
    return _owned_resume(repo, user, resume_id)


@router.get("/resumes/{resume_id}/file")
def download_resume(resume_id: uuid.UUID, user: CurrentUser, repo: Repo) -> Response:
    resume = _owned_resume(repo, user, resume_id)
    data = get_storage().get(resume.storage_key)
    return Response(
        content=data,
        media_type=resume.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{resume.filename}"'},
    )


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(resume_id: uuid.UUID, user: CurrentUser, db: DbSession, repo: Repo) -> Response:
    resume = _owned_resume(repo, user, resume_id)
    try:
        get_storage().delete(resume.storage_key)
    except Exception:
        pass
    db.delete(resume)
    db.commit()
    return Response(status_code=204)


@router.post("/resumes/{resume_id}/analyze", response_model=AnalysisOut)
@limiter.limit(settings.rate_limit_analysis)
def analyze(
    request: Request,
    resume_id: uuid.UUID,
    payload: AnalysisRequest,
    user: CurrentUser,
    db: DbSession,
    repo: Repo,
) -> ResumeAnalysis:
    if user.role != Role.STUDENT.value:
        from app.core.errors import ForbiddenError

        raise ForbiddenError("Only students can analyse resumes")
    resume = _owned_resume(repo, user, resume_id)
    analysis = analyze_resume(
        db,
        user,
        resume,
        job_description=payload.job_description,
        target_role=payload.target_role,
    )
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/resumes/{resume_id}/analyses", response_model=list[AnalysisOut])
def list_analyses(resume_id: uuid.UUID, user: CurrentUser, repo: Repo) -> list[ResumeAnalysis]:
    _owned_resume(repo, user, resume_id)
    return (
        repo.query(ResumeAnalysis)
        .filter(ResumeAnalysis.resume_id == resume_id, ResumeAnalysis.user_id == user.id)
        .order_by(ResumeAnalysis.created_at.desc())
        .all()
    )


@router.get("/analyses/latest", response_model=AnalysisOut)
def latest_analysis_route(user: CurrentUser, repo: Repo) -> ResumeAnalysis:
    analysis = (
        repo.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == user.id)
        .order_by(ResumeAnalysis.created_at.desc())
        .first()
    )
    if analysis is None:
        raise NotFoundError("No resume analysis yet")
    return analysis


@router.patch("/analyses/{analysis_id}/suggestions/{suggestion_id}", response_model=AnalysisOut)
def decide_suggestion(
    analysis_id: uuid.UUID,
    suggestion_id: str,
    payload: SuggestionDecision,
    user: CurrentUser,
    db: DbSession,
    repo: Repo,
) -> ResumeAnalysis:
    analysis = repo.get_or_404(ResumeAnalysis, analysis_id, "Analysis not found")
    if analysis.user_id != user.id:
        raise NotFoundError("Analysis not found")
    set_suggestion_decision(analysis, suggestion_id, payload.accept)
    db.commit()
    db.refresh(analysis)
    return analysis
