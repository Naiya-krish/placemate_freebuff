"""Student dashboard: readiness, radar, gamification, history and next action."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.enums import InterviewStatus
from app.models.interview import Interview
from app.models.resume import Resume, ResumeAnalysis
from app.models.user import College, User
from app.schemas.dashboard import (
    HistoryItem,
    NextAction,
    RadarPoint,
    StudentDashboard,
)
from app.services import gamification

RUBRIC_LABELS = {
    "clarity": "Clarity",
    "technical_depth": "Technical depth",
    "problem_solving": "Problem solving",
    "communication": "Communication",
    "role_fit": "Role fit",
}
RESUME_LABELS = {
    "clarity": "Clarity",
    "impact": "Impact",
    "relevance": "Relevance",
    "structure": "Structure",
    "keywords": "Keywords",
}


def _completed_interviews(db: Session, user: User) -> list[Interview]:
    return (
        db.query(Interview)
        .filter(
            Interview.user_id == user.id,
            Interview.college_id == user.college_id,
            Interview.status == InterviewStatus.COMPLETED.value,
            Interview.overall_score.isnot(None),
        )
        .order_by(Interview.completed_at.desc())
        .all()
    )


def latest_analysis(db: Session, user: User) -> ResumeAnalysis | None:
    return (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.user_id == user.id,
            ResumeAnalysis.college_id == user.college_id,
        )
        .order_by(ResumeAnalysis.created_at.desc())
        .first()
    )


def compute_readiness(interview_score: float | None, resume_score: int | None) -> int:
    if interview_score is not None and resume_score is not None:
        return round(interview_score * 0.7 + resume_score * 0.3)
    if interview_score is not None:
        return round(interview_score)
    if resume_score is not None:
        return resume_score
    return 0


def _radar(interview: Interview | None, analysis: ResumeAnalysis | None) -> list[RadarPoint]:
    if interview and interview.rubric_scores:
        points = []
        for item in interview.rubric_scores:
            score = float(item.get("score", 0))
            points.append(
                RadarPoint(
                    key=str(item.get("key", "")),
                    label=str(item.get("label", item.get("key", ""))),
                    value=round(score * 10),
                )
            )
        return points
    if analysis and analysis.subscores:
        return [
            RadarPoint(
                key=key,
                label=RESUME_LABELS.get(key, key.title()),
                value=int(value),
            )
            for key, value in analysis.subscores.items()
        ]
    return [RadarPoint(key=key, label=label, value=0) for key, label in RUBRIC_LABELS.items()]


def _next_action(
    *,
    has_resume: bool,
    analysis: ResumeAnalysis | None,
    completed: int,
    readiness: int,
    interview: Interview | None,
) -> NextAction:
    if not has_resume:
        return NextAction(
            title="Upload your resume to unlock your score",
            description="A text-based PDF or DOCX gets scored in under a minute, with job-tailored fixes.",
            href="/dashboard/resume",
            cta="Upload resume",
            kind="resume",
        )
    if analysis is None:
        return NextAction(
            title="Score your resume against a target role",
            description="Paste a job description and get accept/reject edits that never invent experience.",
            href="/dashboard/resume",
            cta="Analyse resume",
            kind="analysis",
        )
    if completed == 0:
        return NextAction(
            title="Your first mock interview is ready",
            description="Three rounds, grounded in your projects. Get a rubric score and one next step.",
            href="/dashboard/interviews",
            cta="Start interview",
            kind="interview",
        )
    lowest = min(
        (
            (float(r.get("score", 0)), str(r.get("label", r.get("key", ""))))
            for r in (interview.rubric_scores if interview else [])
        ),
        default=(0.0, "Technical depth"),
    )
    if readiness < 70:
        return NextAction(
            title=f"Lift your weakest area: {lowest[1]}",
            description="One focused interview in this area moves your readiness fastest. Hint costs are off today? No — keep it honest.",
            href="/dashboard/interviews",
            cta="Practise now",
            kind="practice",
        )
    return NextAction(
        title="Tailor your resume for the next drive",
        description="You are above the readiness bar. Tighten keywords for a specific job description.",
        href="/dashboard/resume",
        cta="Tailor resume",
        kind="tailor",
    )


def build_student_dashboard(db: Session, user: User, college: College | None) -> StudentDashboard:
    interviews = _completed_interviews(db, user)
    analysis = latest_analysis(db, user)
    latest = interviews[0] if interviews else None
    previous = interviews[1] if len(interviews) > 1 else None
    resume_count = (
        db.query(Resume)
        .filter(Resume.user_id == user.id, Resume.college_id == user.college_id)
        .count()
    )
    interview_score = (
        round(latest.overall_score) if latest and latest.overall_score is not None else None
    )
    resume_score = analysis.score if analysis else None
    readiness = compute_readiness(
        float(latest.overall_score) if latest and latest.overall_score is not None else None,
        resume_score,
    )
    if latest and latest.overall_score is not None:
        previous_readiness = compute_readiness(
            float(previous.overall_score)
            if previous and previous.overall_score is not None
            else None,
            resume_score,
        )
    else:
        previous_readiness = 0
    delta = readiness - previous_readiness if (latest or analysis) else 0
    delta = delta if latest else 0

    radar = _radar(latest, analysis)
    skill_gaps: list[str] = []
    if analysis:
        skill_gaps = [
            str(item.get("item", "")) for item in analysis.missing_evidence[:3] if item.get("item")
        ]
    if not skill_gaps:
        skill_gaps = [
            point.label for point in sorted(radar, key=lambda p: p.value)[:2] if point.value < 70
        ]

    badges = gamification.badge_catalogue(db, user, resume_score=resume_score, readiness=readiness)
    history: list[HistoryItem] = []
    for interview in interviews[:8]:
        history.append(
            HistoryItem(
                id=interview.id,
                kind="interview",
                title=f"{interview.role.upper()} mock interview",
                subtitle=f"Rubric {interview.rubric_version} · {interview.current_round} completed",
                score=round(interview.overall_score)
                if interview.overall_score is not None
                else None,
                created_at=interview.completed_at or interview.started_at,
            )
        )
    analyses = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == user.id, ResumeAnalysis.college_id == user.college_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .limit(6)
        .all()
    )
    for item in analyses:
        history.append(
            HistoryItem(
                id=item.id,
                kind="resume",
                title=f"Resume score · {item.target_role}",
                subtitle=f"{len(item.suggestions)} supported suggestions",
                score=item.score,
                created_at=item.created_at,
            )
        )
    history.sort(key=lambda h: h.created_at, reverse=True)

    placement_date: date | None = college.placement_date if college else None
    days_to_placement = (placement_date - date.today()).days if placement_date else None
    band = "interview-ready" if readiness >= 70 else "building" if readiness >= 40 else "starting"
    return StudentDashboard(
        readiness=readiness,
        readiness_delta=delta,
        band=band,
        has_resume=resume_count > 0,
        has_interview=bool(interviews),
        radar=radar,
        streak=user.streak_count,
        xp=user.xp,
        level=gamification.level_for(user.xp),
        level_progress=gamification.level_progress(user.xp),
        badges=badges,
        next_action=_next_action(
            has_resume=resume_count > 0,
            analysis=analysis,
            completed=len(interviews),
            readiness=readiness,
            interview=latest,
        ),
        history=history[:10],
        placement_date=placement_date,
        days_to_placement=days_to_placement,
        resume_score=resume_score,
        interview_score=interview_score,
        completed_interviews=len(interviews),
        total_interviews=db.query(Interview).filter(Interview.user_id == user.id).count(),
        skill_gaps=skill_gaps,
    )
