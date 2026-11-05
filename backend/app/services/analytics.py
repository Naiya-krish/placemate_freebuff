"""Officer analytics. Aggregate by default; named rows require student consent."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.enums import InterviewStatus, Role
from app.models.interview import Interview
from app.models.resume import Resume, ResumeAnalysis
from app.models.user import College, User
from app.schemas.officer import (
    BatchRow,
    CohortPoint,
    FunnelStage,
    HeatmapCell,
    OfficerKpis,
    OfficerOverview,
    OfficerStudentRow,
    WeakSkill,
)
from app.services.dashboard import compute_readiness, latest_analysis
from app.services.defaults import ensure_default_rubric


def _week_key(moment: datetime) -> str:
    return f"Wk of {moment.strftime('%d %b')}"


def overview(db: Session, college: College) -> OfficerOverview:
    rubric = ensure_default_rubric(db, college.id)
    students: list[User] = (
        db.query(User).filter(User.college_id == college.id, User.role == Role.STUDENT.value).all()
    )
    student_ids = [s.id for s in students]
    resumes = db.query(Resume).filter(Resume.college_id == college.id).all() if student_ids else []
    analyses = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.college_id == college.id)
        .order_by(ResumeAnalysis.created_at.desc())
        .all()
    )
    interviews = (
        db.query(Interview)
        .filter(
            Interview.college_id == college.id,
            Interview.status == InterviewStatus.COMPLETED.value,
        )
        .order_by(Interview.completed_at.asc())
        .all()
    )

    latest_analysis_by_user: dict[uuid.UUID, ResumeAnalysis] = {}
    for analysis in analyses:
        latest_analysis_by_user.setdefault(analysis.user_id, analysis)
    latest_interview_by_user: dict[uuid.UUID, Interview] = {}
    for interview in interviews:
        latest_interview_by_user[interview.user_id] = interview

    readiness_by_user: dict[uuid.UUID, int] = {}
    for student in students:
        latest_interview = latest_interview_by_user.get(student.id)
        latest_analysis_row = latest_analysis_by_user.get(student.id)
        score = compute_readiness(
            float(latest_interview.overall_score)
            if latest_interview and latest_interview.overall_score is not None
            else None,
            latest_analysis_row.score if latest_analysis_row else None,
        )
        if score > 0:
            readiness_by_user[student.id] = score

    criteria_labels = [str(c["label"]) for c in rubric.criteria]
    criteria_keys = [str(c["key"]) for c in rubric.criteria]
    branches = sorted({student.branch or "Unassigned" for student in students})
    heatmap: list[HeatmapCell] = []
    for branch in branches:
        branch_students = [s for s in students if (s.branch or "Unassigned") == branch]
        branch_interviews = [
            latest_interview_by_user[s.id]
            for s in branch_students
            if s.id in latest_interview_by_user
        ]
        for key, label in zip(criteria_keys, criteria_labels, strict=False):
            values = []
            for interview in branch_interviews:
                for item in interview.rubric_scores or []:
                    if item.get("key") == key:
                        values.append(int(item.get("score", 0)) * 10)
            heatmap.append(
                HeatmapCell(
                    branch=branch,
                    criterion=label,
                    value=round(sum(values) / len(values)) if values else 0,
                    students=len(branch_students),
                )
            )

    total_students = len(students)
    active_cutoff = date.today() - timedelta(days=30)
    active_30d = len(
        [s for s in students if s.last_active_date and s.last_active_date >= active_cutoff]
    )
    completed = len(interviews)
    avg_readiness = (
        round(sum(readiness_by_user.values()) / len(readiness_by_user)) if readiness_by_user else 0
    )

    funnel_counts = [
        ("Registered", total_students),
        ("Resume scored", len({a.user_id for a in analyses})),
        (
            "Interview started",
            len(
                {i.user_id for i in interviews}
                | {
                    i.user_id
                    for i in db.query(Interview).filter(Interview.college_id == college.id).all()
                }
            ),
        ),
        ("Interview scored", len({i.user_id for i in interviews if i.overall_score is not None})),
        ("Readiness 70+", len([v for v in readiness_by_user.values() if v >= 70])),
    ]
    base = max(1, total_students)
    funnel = [
        FunnelStage(stage=name, count=count, percent=round(count / base * 100))
        for name, count in funnel_counts
    ]

    weakest: list[WeakSkill] = []
    interview_criteria: dict[str, list[int]] = defaultdict(list)
    for interview in interviews:
        for item in interview.rubric_scores or []:
            interview_criteria[str(item.get("key", ""))].append(int(item.get("score", 0)) * 10)
    for key, label in zip(criteria_keys, criteria_labels, strict=False):
        values = interview_criteria.get(key, [])
        if not values:
            continue
        average = sum(values) / len(values)
        affected = len([v for v in values if v < 60])
        weakest.append(
            WeakSkill(
                skill=label,
                gap=round(max(0, 100 - average)),
                students_affected=affected,
            )
        )
    if not weakest:
        missing_counts: dict[str, int] = defaultdict(int)
        for analysis in analyses:
            for item in analysis.missing_evidence or []:
                missing_counts[str(item.get("item", "Evidence"))[:40]] += 1
        weakest = [
            WeakSkill(skill=name, gap=60, students_affected=count)
            for name, count in sorted(missing_counts.items(), key=lambda kv: kv[1], reverse=True)[
                :4
            ]
        ]
    weakest.sort(key=lambda w: w.gap, reverse=True)

    weeks: list[CohortPoint] = []
    now = datetime.now(UTC)
    for offset in range(5, -1, -1):
        start = now - timedelta(weeks=offset)
        end = start + timedelta(weeks=1)
        week_interviews = [
            i for i in interviews if i.completed_at and start <= _as_aware(i.completed_at) < end
        ]
        scores = [i.overall_score for i in week_interviews if i.overall_score is not None]
        weeks.append(
            CohortPoint(
                week=_week_key(start),
                interviews=len(week_interviews),
                avg_score=round(sum(scores) / len(scores)) if scores else 0,
            )
        )

    batch_rows: list[BatchRow] = []
    for branch in branches:
        branch_students = [s for s in students if (s.branch or "Unassigned") == branch]
        branch_readiness = [
            readiness_by_user[s.id] for s in branch_students if s.id in readiness_by_user
        ]
        batch_rows.append(
            BatchRow(
                branch=branch,
                students=len(branch_students),
                readiness=round(sum(branch_readiness) / len(branch_readiness))
                if branch_readiness
                else 0,
                interviews=len(
                    [i for i in interviews if i.user_id in {s.id for s in branch_students}]
                ),
                resumes=len([r for r in resumes if r.user_id in {s.id for s in branch_students}]),
            )
        )

    student_rows: list[OfficerStudentRow] = []
    for student in sorted(students, key=lambda s: readiness_by_user.get(s.id, 0), reverse=True):
        consented = bool(student.consent_share_analytics)
        student_interviews = [i for i in interviews if i.user_id == student.id]
        student_rows.append(
            OfficerStudentRow(
                id=student.id,
                display_name=student.name if consented else "Hidden student",
                branch=student.branch,
                readiness=readiness_by_user.get(student.id) if consented else None,
                interviews=len(student_interviews) if consented else 0,
                last_active=student.last_active_date.isoformat()
                if consented and student.last_active_date
                else None,
                consent=consented,
            )
        )

    placement_date = college.placement_date
    return OfficerOverview(
        kpis=OfficerKpis(
            total_students=total_students,
            active_30d=active_30d,
            resume_uploads=len(resumes),
            interviews_completed=completed,
            avg_readiness=avg_readiness,
            placement_date=placement_date,
            days_to_placement=(placement_date - date.today()).days if placement_date else None,
        ),
        heatmap=heatmap,
        criteria=criteria_labels,
        branches=branches,
        funnel=funnel,
        weakest_skills=weakest[:4],
        cohort_progress=weeks,
        batch_comparison=batch_rows,
        students=student_rows,
        generated_at=datetime.now(UTC).isoformat(),
    )


def _as_aware(moment: datetime) -> datetime:
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment


def list_consented_students(db: Session, college: College) -> list[OfficerStudentRow]:
    return [row for row in overview(db, college).students if row.consent]


def latest_analysis_for(db: Session, user: User) -> ResumeAnalysis | None:
    return latest_analysis(db, user)
