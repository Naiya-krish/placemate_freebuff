from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.services.llm.base import LLMMessage, LLMResult  # noqa: F401
from app.services.llm.mock import MockProvider
from tests.conftest import (
    SAMPLE_RESUME,
    analyze,
    auth_headers,
    make_college,
    make_pdf,
    register,
    upload_resume,
)


def _student(client: TestClient, db) -> tuple[dict, str]:
    college = make_college(db)
    account = register(client, college.code, email=f"up{uuid.uuid4().hex[:6]}@example.com")
    return account, account["access_token"]


def test_rejects_wrong_extension_and_fake_magic_bytes(client: TestClient, db) -> None:
    _, token = _student(client, db)
    txt = client.post(
        "/api/v1/resumes",
        headers=auth_headers(token),
        files={"file": ("resume.txt", b"hello world, not a resume", "text/plain")},
    )
    assert txt.status_code == 415
    assert txt.json()["code"] == "unsupported_type"

    fake = client.post(
        "/api/v1/resumes",
        headers=auth_headers(token),
        files={"file": ("resume.pdf", b"this is definitely not a pdf at all", "application/pdf")},
    )
    assert fake.status_code == 415
    assert fake.json()["code"] == "magic_byte_mismatch"

    mismatch = client.post(
        "/api/v1/resumes",
        headers=auth_headers(token),
        files={"file": ("resume.docx", make_pdf(SAMPLE_RESUME), "application/pdf")},
    )
    assert mismatch.status_code == 415


def test_rejects_oversize_upload(client: TestClient, db) -> None:
    _, token = _student(client, db)
    payload = b"%PDF-1.4\n" + b"\x00" * (5 * 1024 * 1024 + 100)
    response = client.post(
        "/api/v1/resumes",
        headers=auth_headers(token),
        files={"file": ("big.pdf", payload, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_accepts_pdf_parses_and_analyses(client: TestClient, db) -> None:
    _, token = _student(client, db)
    resume = upload_resume(client, token, SAMPLE_RESUME)
    assert resume["status"] == "parsed"
    assert resume["parsed_data"]["skills"]
    assert any(skill.lower() == "python" for skill in resume["parsed_data"]["skills"])

    analysis = analyze(
        client,
        token,
        resume["id"],
        "Backend role: Python, FastAPI, PostgreSQL, testing, Docker, cloud deployment, Kubernetes.",
    )
    assert 0 <= analysis["score"] <= 100
    assert set(analysis["subscores"]) == {"clarity", "impact", "relevance", "structure", "keywords"}
    assert analysis["prompt_version"] == "v1"
    assert analysis["model"] == "mock"
    assert isinstance(analysis["missing_evidence"], list)

    if analysis["suggestions"]:
        suggestion = analysis["suggestions"][0]
        assert suggestion["supported"] is True
        decision = client.patch(
            f"/api/v1/analyses/{analysis['id']}/suggestions/{suggestion['id']}",
            headers=auth_headers(token),
            json={"accept": True},
        )
        assert decision.status_code == 200, decision.text
        updated = next(s for s in decision.json()["suggestions"] if s["id"] == suggestion["id"])
        assert updated["decision"] == "accepted"


def test_accepts_docx_with_magic_bytes(client: TestClient, db) -> None:
    from io import BytesIO

    from docx import Document

    _, token = _student(client, db)
    document = Document()
    document.add_paragraph("Meera Nair")
    document.add_paragraph("meera@example.edu | +91 9876543210")
    document.add_paragraph("Skills")
    document.add_paragraph("Python, SQL, React")
    document.add_paragraph("Projects")
    document.add_paragraph("CampusRide")
    document.add_paragraph("- Built a ride-sharing service with FastAPI")
    buffer = BytesIO()
    document.save(buffer)
    response = client.post(
        "/api/v1/resumes",
        headers=auth_headers(token),
        files={
            "file": (
                "resume.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "parsed"


def test_resume_never_invents_experience(client: TestClient, db, monkeypatch) -> None:
    from app.core.config import settings

    _, token = _student(client, db)
    resume = upload_resume(client, token, SAMPLE_RESUME)
    monkeypatch.setattr(settings, "mock_llm_hallucinate", True)
    analysis = analyze(client, token, resume["id"])
    joined = " ".join(s["improved"] for s in analysis["suggestions"])
    assert "Google" not in joined
    assert "40%" not in joined
    assert any("Unverified edit" in item["item"] for item in analysis["missing_evidence"])


def test_mock_provider_is_deterministic() -> None:
    provider = MockProvider()
    kwargs = dict(
        model="mock",
        temperature=0.2,
        max_tokens=100,
        task="resume_analysis",
        variables={"resume_text": SAMPLE_RESUME, "job_description": "Python", "target_role": "SWE"},
    )
    first = provider.generate([LLMMessage(role="user", content="x")], **kwargs)
    second = provider.generate([LLMMessage(role="user", content="x")], **kwargs)
    assert first.text == second.text
    assert first.input_tokens > 0
