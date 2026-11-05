#!/usr/bin/env python3
"""Idempotent demo seed: one college, staff, 14 students, resumes, analyses and interviews.

Usage: python scripts/seed_demo_data.py [--if-empty]
Credentials are printed at the end (all demo accounts use one local password).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import InterviewStatus, Round, Role, Speaker  # noqa: E402
from app.models.interview import Interview, InterviewScore, InterviewTurn  # noqa: E402
from app.models.resume import Resume, ResumeAnalysis  # noqa: E402
from app.models.rubric import RubricVersion  # noqa: E402
from app.models.usage import UsageEvent  # noqa: E402
from app.models.user import College, User  # noqa: E402
from app.services.defaults import (  # noqa: E402
    DEFAULT_CRITERIA,
    DEFAULT_RUBRIC_VERSION,
    rubric_weights,
)

DEMO_PASSWORD = "Demo@1234"
COLLEGE_CODE = "NOVA"
COLLEGE_NAME = "Nova Institute of Technology"

STUDENT_ROWS = [
    # name, branch, role, consent, xp, streak, resume_score, interview_scores
    ("Aarav Sharma", "CSE", "Software Engineer", True, 640, 5, 78, [66, 74]),
    ("Ananya Rao", "CSE", "Backend Engineer", True, 520, 3, 71, [69]),
    ("Rohan Mehta", "IT", "Software Engineer", False, 310, 2, 63, [58]),
    ("Ishita Sen", "ECE", "Core Electronics", True, 780, 7, 82, [81, 86]),
    ("Karan Patel", "ECE", "VLSI Engineer", False, 120, 1, 54, []),
    ("Meera Nair", "IT", "Data Analyst", True, 450, 4, 74, [72]),
    ("Aditya Verma", "CSE", "Data Scientist", False, 260, 2, 68, [61]),
    ("Sneha Iyer", "EEE", "Core Electronics", False, 90, 0, 49, []),
    ("Arjun Das", "MECH", "Core Electronics", False, 60, 0, 45, []),
    ("Priya Sharma", "CSE", "Product Manager", True, 590, 6, 80, [77, 83]),
    ("Nikhil Reddy", "IT", "Software Engineer", False, 380, 3, 66, [55, 62]),
    ("Tanvi Joshi", "ECE", "Data Analyst", True, 430, 2, 70, [68]),
    ("Dev Malhotra", "CSE", "Software Engineer", False, 210, 1, 59, []),
    ("Sara Khan", "CSE", "Software Engineer", True, 300, 4, 72, [70]),
]

PROJECT_POOL = [
    ("CampusRide", "A campus ride-sharing backend with live matching and fare estimates.", ["FastAPI", "PostgreSQL", "Redis"]),
    ("InsightBoard", "A React analytics dashboard used by student clubs to track engagement.", ["React", "TypeScript", "SQL"]),
    ("NeuralNotes", "A study-notes summariser fine-tuned on lecture transcripts.", ["Python", "PyTorch", "FastAPI"]),
    ("GreenGrid", "An IoT energy monitor for hostel blocks with anomaly alerts.", ["Embedded C", "MQTT", "Python"]),
    ("RouteOne", "A logistics route optimiser for a local delivery cooperative.", ["Python", "OR-Tools", "PostgreSQL"]),
    ("SafeAlert", "A low-power wearable panic button with SMS fallback.", ["Embedded C", "GSM", "PCB Design"]),
    ("SkillGraph", "A graph-based recommendation engine for peer learning.", ["Neo4j", "Python", "FastAPI"]),
    ("CityPulse", "A public transport delay predictor from open transit feeds.", ["Python", "Pandas", "scikit-learn"]),
]

SKILLS_BY_BRANCH = {
    "CSE": ["Python", "FastAPI", "PostgreSQL", "React", "Docker", "Git"],
    "IT": ["Java", "Spring Boot", "MySQL", "REST APIs", "Git", "Docker"],
    "ECE": ["Embedded C", "Verilog", "MATLAB", "Microcontrollers", "Python", "PCB Design"],
    "EEE": ["MATLAB", "Power Systems", "Python", "Circuit Design", "PLC"],
    "MECH": ["SolidWorks", "AutoCAD", "Thermodynamics", "Python", "Manufacturing"],
}

CRITERIA_LABELS = {
    "clarity": "Clarity",
    "technical_depth": "Technical depth",
    "problem_solving": "Problem solving",
    "communication": "Communication",
    "role_fit": "Role fit",
}


def _resume_text(name: str, branch: str, role: str, projects: list[tuple[str, str, list[str]]]) -> str:
    skills = ", ".join(SKILLS_BY_BRANCH.get(branch, SKILLS_BY_BRANCH["CSE"]))
    lines = [
        name,
        f"{name.lower().replace(' ', '.')}@example.edu | +91 9876543210 | https://github.com/example",
        "",
        "Summary",
        f"Final-year {branch} student targeting {role} roles. Builds practical projects and enjoys",
        "turning ambiguous problems into shipped, tested software.",
        "",
        "Skills",
        skills,
        "",
        "Experience",
        "Engineering Intern | TechNova",
        "- Worked on internal APIs used by the operations team",
        "- Helped with database migrations and query tuning",
        "- Wrote pytest coverage for the ingestion pipeline",
        "",
        "Projects",
    ]
    for project_name, description, tech in projects:
        lines.extend(
            [
                project_name,
                f"- Built {description}",
                f"- Used {', '.join(tech)} and measured the result before shipping",
                "- Documented trade-offs and wrote integration tests",
            ]
        )
    lines.extend(
        [
            "",
            "Education",
            "Nova Institute of Technology",
            f"B.Tech in {branch}, 2026",
            "",
            "Achievements",
            "- Runner-up, institute hackathon 2025",
        ]
    )
    return "\n".join(lines)


def _parsed(name: str, branch: str, projects: list[tuple[str, str, list[str]]]) -> dict:
    return {
        "full_name": name,
        "email": f"{name.lower().replace(' ', '.')}@example.edu",
        "phone": "+91 9876543210",
        "links": ["https://github.com/example"],
        "summary": f"Final-year {branch} student building practical software with measurable outcomes.",
        "skills": SKILLS_BY_BRANCH.get(branch, SKILLS_BY_BRANCH["CSE"]),
        "experience": [
            {
                "company": "TechNova",
                "title": "Engineering Intern",
                "start": "May 2025",
                "end": "Jul 2025",
                "location": "Bengaluru",
                "bullets": [
                    "Worked on internal APIs used by the operations team",
                    "Helped with database migrations and query tuning",
                ],
            }
        ],
        "projects": [
            {"name": name_, "description": desc, "tech": tech, "bullets": ["Built the core service", "Added tests"]}
            for name_, desc, tech in projects
        ],
        "education": [
            {
                "institution": "Nova Institute of Technology",
                "degree": "B.Tech",
                "field": branch,
                "start": "2022",
                "end": "2026",
                "score": "8.4 CGPA",
            }
        ],
        "certifications": ["Cloud fundamentals"],
        "achievements": ["Runner-up, institute hackathon 2025"],
    }


def _criteria_for(weights: dict[str, float], base: float) -> list[dict]:
    return [
        {
            "key": key,
            "label": CRITERIA_LABELS[key],
            "weight": weights[key],
            "score": max(2, min(9, round(base))),
            "note": "Cited a concrete project decision and its outcome; the trade-off was explained.",
            "improvement": {
                "clarity": "Lead with the outcome in the first sentence.",
                "technical_depth": "Name the constraint and the alternative you rejected.",
                "problem_solving": "Show how you validated the fix after shipping.",
                "communication": "Close with what you learned.",
                "role_fit": "Connect the example to the target role explicitly.",
            }[key],
        }
        for key in weights
    ]


def _weighted_score(criteria: list[dict]) -> float:
    return round(sum(c["score"] / 10 * c["weight"] * 100 for c in criteria), 1)


def seed() -> None:
    with SessionLocal() as db:
        college = db.query(College).filter(College.code == COLLEGE_CODE).one_or_none()
        if college is not None:
            print(f"college {COLLEGE_CODE} already seeded; nothing to do")
            return

        college = College(
            name=COLLEGE_NAME,
            code=COLLEGE_CODE,
            city="Bengaluru",
            placement_date=date.today() + timedelta(days=76),
        )
        db.add(college)
        db.flush()

        rubric = RubricVersion(
            college_id=college.id,
            version=DEFAULT_RUBRIC_VERSION,
            label="PlaceMate standard rubric v1",
            criteria=DEFAULT_CRITERIA,
            is_active=True,
        )
        db.add(rubric)
        db.flush()
        weights = rubric_weights(DEFAULT_CRITERIA)

        def add_user(
            email: str,
            name: str,
            role: str,
            branch: str,
            target_role: str,
            *,
            consent: bool = False,
            xp: int = 0,
            streak: int = 0,
        ) -> User:
            user = User(
                college_id=college.id,
                email=email,
                name=name,
                hashed_password=hash_password(DEMO_PASSWORD),
                role=role,
                branch=branch,
                target_role=target_role,
                consent_share_analytics=consent,
                consent_policy_version="2026-01",
                onboarding_complete=True,
                xp=xp,
                streak_count=streak,
                last_active_date=date.today() - timedelta(days=0 if streak else 2),
            )
            db.add(user)
            db.flush()
            return user

        admin = add_user("admin@placemate.dev", "Dr. Nandita Bose", Role.ADMIN.value, "Administration", "Placement Head", consent=True)
        add_user("officer@placemate.dev", "Vikram Desai", Role.OFFICER.value, "Placement Cell", "Placement Officer", consent=True)
        student_user = add_user("student@placemate.dev", "Aarav Sharma", Role.STUDENT.value, "CSE", "Software Engineer", consent=True, xp=640, streak=5)

        students: list[User] = [student_user]
        for index, (name, branch, role, consent, xp, streak, _score, _interviews) in enumerate(STUDENT_ROWS):
            if index == 0:
                continue
            email = f"{name.lower().replace(' ', '.')}@example.edu"
            students.append(add_user(email, name, Role.STUDENT.value, branch, role, consent=consent, xp=xp, streak=streak))

        now = datetime.now(UTC)
        monthly = now.strftime("%Y-%m")
        usage_total = 0.0

        for index, (name, branch, role, _consent, _xp, _streak, resume_score, interview_scores) in enumerate(STUDENT_ROWS):
            user = students[index]
            projects = [PROJECT_POOL[(index + offset) % len(PROJECT_POOL)] for offset in range(2)]
            text = _resume_text(name, branch, role, projects)
            created = now - timedelta(days=34 - index)
            resume = Resume(
                college_id=college.id,
                user_id=user.id,
                filename=f"{name.lower().replace(' ', '-')}-resume.pdf",
                storage_key=f"{college.id}/{user.id}/{uuid.uuid4().hex}.pdf",
                mime_type="application/pdf",
                size_bytes=48_000 + index * 1200,
                sha256=uuid.uuid4().hex * 2,
                status="parsed",
                used_ocr=False,
                pages=1,
                raw_text=text,
                parsed_data=_parsed(name, branch, projects),
                warnings=[],
                created_at=created,
            )
            db.add(resume)
            db.flush()

            subscores = {
                "clarity": min(94, resume_score + 3),
                "impact": max(35, resume_score - 6),
                "relevance": min(93, resume_score + 1),
                "structure": min(90, resume_score + 2),
                "keywords": max(40, resume_score - 2),
            }
            suggestions = [
                {
                    "id": uuid.uuid4().hex[:12],
                    "target_section": "experience",
                    "category": "impact",
                    "original": "Worked on internal APIs used by the operations team",
                    "improved": "Built internal APIs used by the operations team",
                    "rationale": "A stronger opening verb improves impact without adding facts.",
                    "supported": True,
                    "decision": "accepted" if index % 2 == 0 else "pending",
                },
                {
                    "id": uuid.uuid4().hex[:12],
                    "target_section": "experience",
                    "category": "clarity",
                    "original": "Helped with database migrations and query tuning",
                    "improved": "Contributed to database migrations and query tuning",
                    "rationale": "Clear ownership framing is easier for a recruiter to scan.",
                    "supported": True,
                    "decision": "pending",
                },
            ]
            analysis = ResumeAnalysis(
                college_id=college.id,
                user_id=user.id,
                resume_id=resume.id,
                target_role=role,
                job_description=(
                    f"Hiring a {role} with strong fundamentals, practical project experience, "
                    "testing discipline and clear communication. Cloud deployment is a plus."
                ),
                score=resume_score,
                subscores=subscores,
                suggestions=suggestions,
                missing_evidence=[
                    {
                        "item": "Quantified business impact",
                        "reason": "Bullets describe work but rarely state the number that changed.",
                    },
                    {
                        "item": "Deployment evidence",
                        "reason": "The resume does not say where a project ran or who used it.",
                    },
                ],
                injection_flags=[],
                prompt_version="v1",
                model="mock",
                created_at=created + timedelta(minutes=2),
            )
            db.add(analysis)
            db.add(
                UsageEvent(
                    college_id=college.id,
                    user_id=user.id,
                    feature="resume_analysis",
                    model="mock",
                    input_tokens=1800 + index * 20,
                    output_tokens=420,
                    cost_usd=0.0003,
                    month=monthly,
                    created_at=created + timedelta(minutes=2),
                )
            )
            usage_total += 0.0003

            for round_index, score in enumerate(interview_scores):
                completed = now - timedelta(days=18 - index, hours=round_index * 3)
                started = completed - timedelta(minutes=22)
                criteria = _criteria_for(weights, (score - 8) / 10)
                overall = _weighted_score(criteria)
                interview = Interview(
                    college_id=college.id,
                    user_id=user.id,
                    resume_id=resume.id,
                    role="swe" if "Engineer" in role or "Software" in role else "data" if "Data" in role else "core" if "Electronics" in role or "VLSI" in role else "product",
                    status=InterviewStatus.COMPLETED.value,
                    current_round=Round.HR.value,
                    current_index=3,
                    followups_asked=1,
                    hint_count=1 if index % 3 == 0 else 0,
                    rubric_version=DEFAULT_RUBRIC_VERSION,
                    prompt_version="v1",
                    model="mock",
                    overall_score=overall,
                    rubric_scores=criteria,
                    feedback={
                        "summary": "Comfortable explaining project decisions; the next step is sharper metrics.",
                        "strengths": [
                            "Explained the architecture before diving into details.",
                            "Owned a concrete debugging story end to end.",
                        ],
                        "improvements": [
                            "Quantify the result of the optimisation you described.",
                            "State the alternative you rejected and why.",
                        ],
                        "samples_used": 3,
                        "spread": 0.0,
                        "needs_review": False,
                        "rubric_label": "PlaceMate standard rubric v1",
                    },
                    variance_flag=False,
                    needs_review=False,
                    duration_seconds=1240 + index * 30,
                    started_at=started,
                    completed_at=completed,
                )
                db.add(interview)
                db.flush()

                first_project = projects[0]
                transcript = [
                    (
                        Round.PROJECT.value,
                        f"Walk me through {first_project[0]}: what problem did it solve and what did you own?",
                        f"I owned the backend for {first_project[0]}. The problem was that student clubs had no shared view of engagement. I designed the API, modelled the data in PostgreSQL and added caching, which cut p95 latency from 420 ms to 260 ms.",
                        False,
                    ),
                    (
                        Round.PROJECT.value,
                        f"What trade-off did you make in {first_project[0]}, and what would you change now?",
                        "I chose a monolith to ship faster instead of splitting services. It was the right call for a small team, but I would extract the ingestion worker first because it has a different scaling profile.",
                        True,
                    ),
                    (
                        Round.TECHNICAL.value,
                        "How does database indexing work and when can an index hurt?",
                        "An index is a B-tree that trades write cost and storage for faster reads. It hurts when selectivity is low or when write volume dominates, because every insert updates the index.",
                        False,
                    ),
                    (
                        Round.TECHNICAL.value,
                        "How did you test the critical path before shipping?",
                        "I wrote integration tests against a real Postgres instance, covered the failure path where Redis was unavailable, and added request-level logging so we could debug production issues.",
                        True,
                    ),
                    (
                        Round.HR.value if round_index else Round.HR.value,
                        "Tell me about a time you disagreed with a teammate.",
                        "My teammate wanted to skip pagination for the first release. I showed that the demo data already exceeded one page and we agreed to add cursor pagination before launch.",
                        False,
                    ),
                    (
                        Round.HR.value,
                        "Where do you want to be in three years?",
                        f"I want to be a dependable {role} who can own a service end to end and mentor juniors. In my first month I would learn the codebase, ship a small fix and document what I learned.",
                        False,
                    ),
                ]
                for turn_index, (round_name, question, answer, followup) in enumerate(transcript):
                    db.add(
                        InterviewTurn(
                            college_id=college.id,
                            interview_id=interview.id,
                            idx=turn_index * 2,
                            round=round_name,
                            speaker=Speaker.INTERVIEWER.value,
                            content=question,
                            is_followup=followup,
                            created_at=started + timedelta(minutes=turn_index * 3),
                        )
                    )
                    db.add(
                        InterviewTurn(
                            college_id=college.id,
                            interview_id=interview.id,
                            idx=turn_index * 2 + 1,
                            round=round_name,
                            speaker=Speaker.CANDIDATE.value,
                            content=answer,
                            created_at=started + timedelta(minutes=turn_index * 3 + 1),
                        )
                    )
                db.add(
                    InterviewScore(
                        college_id=college.id,
                        interview_id=interview.id,
                        samples=[{"criteria": criteria, "summary": "Demo sample", "strengths": [], "improvements": []}] * 3,
                        medians=criteria,
                        overall=overall,
                        spread=0.0,
                        variance_flag=False,
                        needs_review=False,
                        rubric_version=DEFAULT_RUBRIC_VERSION,
                        prompt_version="v1",
                        model="mock",
                        created_at=completed,
                    )
                )
                db.add(
                    UsageEvent(
                        college_id=college.id,
                        user_id=user.id,
                        feature="interview_scoring",
                        model="mock",
                        input_tokens=4200,
                        output_tokens=780,
                        cost_usd=0.0009,
                        month=monthly,
                        created_at=completed,
                    )
                )
                usage_total += 0.0009

        db.commit()
        print(f"seeded {COLLEGE_NAME} ({COLLEGE_CODE})")
        print(f"  students: {len(students)}  demo AI usage: ${usage_total:.4f}")
        print("  accounts (password for all: Demo@1234):")
        print("    student@placemate.dev  → student dashboard")
        print("    officer@placemate.dev  → aggregate analytics + PDF")
        print("    admin@placemate.dev    → colleges, question bank, rubrics, usage")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-empty", action="store_true")
    args = parser.parse_args()
    if args.if_empty:
        with SessionLocal() as db:
            if db.query(College).filter(College.code == COLLEGE_CODE).first():
                print("demo data already present; skipping")
                return 0
    seed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
