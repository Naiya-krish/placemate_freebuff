"""Test configuration. Runs entirely on SQLite + mock LLM: no external services."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_placemate.db"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-that-is-long-enough"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DEMO_MODE"] = "true"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_DIR"] = "./storage/test-uploads"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["RATE_LIMIT_AUTH"] = "10000/minute"
os.environ["RATE_LIMIT_DEFAULT"] = "10000/minute"
os.environ["RATE_LIMIT_UPLOAD"] = "10000/minute"
os.environ["RATE_LIMIT_ANALYSIS"] = "10000/minute"
os.environ["RATE_LIMIT_INTERVIEW"] = "10000/minute"
os.environ["PER_USER_MONTHLY_BUDGET"] = "5.00"
os.environ["API_PUBLIC_URL"] = "http://localhost:8000"
os.environ["FRONTEND_URL"] = "http://localhost:3000"

import fitz  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import Role  # noqa: E402
from app.models.rubric import RubricVersion  # noqa: E402
from app.models.user import College, User  # noqa: E402
from app.services.defaults import DEFAULT_CRITERIA, DEFAULT_RUBRIC_VERSION  # noqa: E402

DEMO_PASSWORD = "Password123!"
PDF_TYPE = "application/pdf"


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Path("./storage/test-uploads").mkdir(parents=True, exist_ok=True)
    yield
    Base.metadata.drop_all(engine)
    Path("./test_placemate.db").unlink(missing_ok=True)


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_college(db, *, code: str | None = None, name: str = "Test Institute") -> College:
    suffix = uuid.uuid4().hex[:6].upper()
    college = College(
        name=f"{name} {suffix}",
        code=code or f"T{suffix}",
        city="Bengaluru",
        placement_date=(datetime.now(UTC) + timedelta(days=60)).date(),
    )
    db.add(college)
    db.flush()
    db.add(
        RubricVersion(
            college_id=college.id,
            version=DEFAULT_RUBRIC_VERSION,
            label="Test rubric",
            criteria=DEFAULT_CRITERIA,
            is_active=True,
        )
    )
    db.commit()
    db.refresh(college)
    return college


def make_user(
    db,
    college: College,
    *,
    email: str | None = None,
    role: str = Role.STUDENT.value,
    name: str = "Test Student",
    branch: str = "CSE",
    consent: bool = False,
) -> User:
    user = User(
        college_id=college.id,
        email=email or f"user{uuid.uuid4().hex[:8]}@example.com",
        name=name,
        hashed_password=hash_password(DEMO_PASSWORD),
        role=role,
        branch=branch,
        target_role="Software Engineer",
        consent_share_analytics=consent,
        onboarding_complete=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(
    client: TestClient,
    college_code: str,
    *,
    email: str | None = None,
    password: str = DEMO_PASSWORD,
    name: str = "Aarav Sharma",
    branch: str = "CSE",
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "college_code": college_code,
            "name": name,
            "email": email or f"student{uuid.uuid4().hex[:8]}@example.com",
            "password": password,
            "branch": branch,
            "target_role": "Software Engineer",
            "consent_notice": True,
            "share_analytics": False,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    lines = text.splitlines()
    y = 60
    for line in lines:
        page.insert_text((54, y), line[:110], fontsize=9)
        y += 12
        if y > 780:
            page = doc.new_page()
            y = 60
    data = doc.tobytes()
    doc.close()
    return data


def upload_resume(client: TestClient, token: str, text: str, filename: str = "resume.pdf") -> dict:
    response = client.post(
        "/api/v1/resumes",
        headers=auth_headers(token),
        files={"file": (filename, make_pdf(text), PDF_TYPE)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def analyze(client: TestClient, token: str, resume_id: str, job_description: str = "") -> dict:
    response = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers=auth_headers(token),
        json={
            "job_description": job_description
            or "We need a software engineer with Python, SQL, APIs, testing and cloud deployment experience.",
            "target_role": "Software Engineer",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def assert_settings_budget(monkeypatch: pytest.MonkeyPatch, value: float) -> None:
    monkeypatch.setattr(settings, "per_user_monthly_budget", value)


SAMPLE_RESUME = """Aarav Sharma
aarav.sharma@example.com | +91 9876543210 | https://github.com/aarav

Summary
Final-year Computer Science student building backend systems and data products.

Skills
Python, FastAPI, PostgreSQL, React, Docker, Git

Experience
Backend Intern | Zeta Systems
- Worked on REST APIs for the payments dashboard
- Helped with database migrations and query tuning
- Built internal tooling used by the support team

Projects
CampusRide
- Built a ride-sharing backend with FastAPI and PostgreSQL
- Added Redis caching that reduced average response time by 38%
InsightBoard
- Created a React analytics dashboard for student clubs
- Wrote pytest coverage for the ingestion pipeline

Education
Nova Institute of Technology
B.Tech in Computer Science, 2026

Achievements
- Winner, college hackathon 2025
"""
