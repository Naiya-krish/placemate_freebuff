"""Resume upload, structured parsing and analysis."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AIOutputError
from app.core.tenancy import TenantRepository
from app.models.resume import Resume, ResumeAnalysis
from app.models.user import User
from app.prompts import prompt_version
from app.schemas.ai import AnalysisAI, ResumeParseAI
from app.services import gamification
from app.services.llm.client import LLMClient
from app.services.resume_parser import extract_text, validate_upload
from app.services.safety import (
    check_suggestion_evidence,
    detect_injection,
    fence_untrusted,
    sanitize_text,
)
from app.services.storage import get_storage

logger = logging.getLogger(__name__)


def parse_resume(
    db: Session, user: User, resume: Resume, client: LLMClient | None = None
) -> Resume:
    """Parse stored resume text into structured JSON using the cheap model."""
    llm = client or LLMClient(db, user, feature="resume_parse")
    if len(resume.raw_text.strip()) < 20:
        resume.status = "needs_review"
        resume.warnings = [*resume.warnings, "Not enough text to parse automatically."]
        return resume
    variables = {
        "resume_block": fence_untrusted("RESUME", resume.raw_text, max_chars=20_000),
        "resume_text": sanitize_text(resume.raw_text, max_chars=20_000),
    }
    try:
        parsed, _ = llm.structured("resume_parse", variables, ResumeParseAI, retries=1)
        resume.parsed_data = parsed.model_dump()
        resume.status = "parsed"
    except (AIOutputError, ValidationError) as exc:
        logger.warning("resume_parse_failed resume=%s error=%s", resume.id, type(exc).__name__)
        resume.parsed_data = _fallback_parse(resume.raw_text)
        resume.status = "needs_review"
        resume.warnings = [*resume.warnings, "Automatic structure parsing needs a quick review."]
    return resume


def _fallback_parse(text: str) -> dict[str, Any]:
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    return {
        "full_name": (text.strip().splitlines()[0][:120] if text.strip() else ""),
        "email": email.group(0) if email else "",
        "phone": "",
        "links": [],
        "summary": "",
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "achievements": [],
    }


def create_resume(
    db: Session,
    repo: TenantRepository,
    user: User,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> Resume:
    ext = validate_upload(filename, content_type, data)
    digest = hashlib.sha256(data).hexdigest()
    key = f"{user.college_id}/{user.id}/{uuid.uuid4().hex}{ext}"
    storage = get_storage()
    storage.put(
        key,
        data,
        "application/pdf"
        if ext == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    parsed_doc = extract_text(ext, data)
    safe_filename = re.sub(r"[^A-Za-z0-9._ -]", "_", filename)[:180]
    resume = Resume(
        college_id=user.college_id,
        user_id=user.id,
        filename=safe_filename,
        storage_key=key,
        mime_type="application/pdf"
        if ext == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=len(data),
        sha256=digest,
        status="parsed",
        used_ocr=parsed_doc.used_ocr,
        pages=parsed_doc.pages,
        raw_text=parsed_doc.text,
        parsed_data={},
        warnings=parsed_doc.warnings,
    )
    repo.add(resume)
    db.flush()

    if parsed_doc.text.strip():
        parse_resume(db, user, resume)
    else:
        resume.status = "needs_review"
    gamification.touch_streak(user)
    gamification.award_xp(user, 15)
    db.flush()
    return resume


def analyze_resume(
    db: Session,
    user: User,
    resume: Resume,
    *,
    job_description: str,
    target_role: str | None,
    client: LLMClient | None = None,
) -> ResumeAnalysis:
    if not resume.raw_text.strip():
        raise AIOutputError("This resume has no extractable text. Upload a text-based PDF or DOCX.")

    role = (target_role or user.target_role or "Software Engineer")[:80]
    jd = sanitize_text(job_description, max_chars=6000)
    injection_flags = sorted(set(detect_injection(resume.raw_text) + detect_injection(jd)))

    variables = {
        "target_role": role,
        "resume_block": fence_untrusted("RESUME", resume.raw_text, max_chars=18_000),
        "job_description_block": fence_untrusted(
            "JOB_DESCRIPTION",
            jd or "No job description supplied; target the stated role.",
            max_chars=6000,
        ),
        "resume_text": sanitize_text(resume.raw_text, max_chars=18_000),
        "job_description": jd,
    }
    llm = client or LLMClient(db, user, feature="resume_analysis")
    result, _meta = llm.structured("resume_analysis", variables, AnalysisAI, retries=1)

    known_skills = {
        str(s).lower() for s in (resume.parsed_data.get("skills") or []) if isinstance(s, str)
    }
    suggestions_out: list[dict[str, Any]] = []
    missing_out: list[dict[str, Any]] = [
        {"item": item.item, "reason": item.reason} for item in result.missing_evidence
    ]
    for suggestion in result.suggestions:
        evidence = check_suggestion_evidence(
            original=suggestion.original,
            improved=suggestion.improved,
            resume_text=resume.raw_text,
            known_skills=known_skills,
        )
        record = {
            "id": uuid.uuid4().hex[:12],
            "target_section": suggestion.target_section,
            "category": suggestion.category,
            "original": suggestion.original,
            "improved": suggestion.improved,
            "rationale": suggestion.rationale,
            "supported": evidence.supported,
            "decision": "pending",
        }
        if evidence.supported:
            suggestions_out.append(record)
        else:
            missing_out.append(
                {
                    "item": f"Unverified edit in {suggestion.target_section}",
                    "reason": "Suggestion blocked: " + "; ".join(evidence.reasons[:3]),
                }
            )

    analysis = ResumeAnalysis(
        college_id=user.college_id,
        user_id=user.id,
        resume_id=resume.id,
        target_role=role,
        job_description=jd,
        score=max(0, min(100, result.overall_score)),
        subscores=result.subscores.model_dump(),
        suggestions=suggestions_out,
        missing_evidence=missing_out[:15],
        injection_flags=injection_flags,
        prompt_version=prompt_version("resume_analysis"),
        model=_meta.model,
    )
    db.add(analysis)
    gamification.touch_streak(user)
    gamification.award_xp(user, 25)
    db.flush()
    return analysis


def latest_analysis(
    db: Session, user: User, resume_id: uuid.UUID | None = None
) -> ResumeAnalysis | None:
    query = db.query(ResumeAnalysis).filter(ResumeAnalysis.user_id == user.id)
    if resume_id:
        query = query.filter(ResumeAnalysis.resume_id == resume_id)
    return query.order_by(ResumeAnalysis.created_at.desc()).first()


def set_suggestion_decision(
    analysis: ResumeAnalysis, suggestion_id: str, accept: bool
) -> dict[str, Any]:
    from sqlalchemy.orm.attributes import flag_modified

    updated: list[dict[str, Any]] = []
    found: dict[str, Any] | None = None
    for suggestion in analysis.suggestions or []:
        item = dict(suggestion)
        if item.get("id") == suggestion_id:
            item["decision"] = "accepted" if accept else "rejected"
            found = item
        updated.append(item)
    if found is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Suggestion not found")
    analysis.suggestions = updated
    flag_modified(analysis, "suggestions")
    return found


def resume_skill_profile(resume: Resume) -> set[str]:
    skills = resume.parsed_data.get("skills") if resume.parsed_data else []
    return {str(s).lower() for s in skills or []}


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}"


__all__ = [
    "analyze_resume",
    "create_resume",
    "latest_analysis",
    "parse_resume",
    "set_suggestion_decision",
    "settings",
]
