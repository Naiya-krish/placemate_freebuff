from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.user import User
from tests.conftest import (
    SAMPLE_RESUME,
    auth_headers,
    login,
    make_college,
    make_user,
    register,
    upload_resume,
)


def test_registration_requires_consent_and_records_choice(client: TestClient, db) -> None:
    college = make_college(db)
    bad = client.post(
        "/api/v1/auth/register",
        json={
            "college_code": college.code,
            "name": "No Consent",
            "email": f"no{uuid.uuid4().hex[:6]}@example.com",
            "password": "Password123!",
            "branch": "CSE",
            "target_role": "Software Engineer",
            "consent_notice": False,
        },
    )
    assert bad.status_code == 422

    good = register(client, college.code)
    assert good["user"]["role"] == "student"
    assert good["user"]["consent_share_analytics"] is False
    me = client.get("/api/v1/auth/me", headers=auth_headers(good["access_token"]))
    assert me.status_code == 200
    assert me.json()["college_name"].startswith(college.name.split()[0])


def test_duplicate_email_and_bad_password(client: TestClient, db) -> None:
    college = make_college(db)
    account = register(client, college.code, email=f"dup{uuid.uuid4().hex[:6]}@example.com")
    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "college_code": college.code,
            "name": "Duplicate",
            "email": account["user"]["email"],
            "password": "Password123!",
            "branch": "CSE",
            "target_role": "Software Engineer",
            "consent_notice": True,
        },
    )
    assert duplicate.status_code == 409
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": account["user"]["email"], "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert "Incorrect" in wrong.json()["detail"]


def test_refresh_token_rotation_rejects_replay(client: TestClient, db) -> None:
    college = make_college(db)
    register(client, college.code)
    old_cookie = client.cookies.get("placemate_refresh")
    assert old_cookie
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    new_cookie = client.cookies.get("placemate_refresh")
    assert new_cookie and new_cookie != old_cookie
    replay = client.post("/api/v1/auth/refresh", cookies={"placemate_refresh": old_cookie})
    assert replay.status_code == 401


def test_tenant_isolation_across_colleges(client: TestClient, db) -> None:
    college_a = make_college(db)
    college_b = make_college(db)
    account_a = register(client, college_a.code, email=f"a{uuid.uuid4().hex[:6]}@example.com")
    account_b = register(client, college_b.code, email=f"b{uuid.uuid4().hex[:6]}@example.com")
    token_a = account_a["access_token"]
    token_b = account_b["access_token"]

    resume = upload_resume(client, token_a, SAMPLE_RESUME)
    analysis = client.post(
        f"/api/v1/resumes/{resume['id']}/analyze",
        headers=auth_headers(token_a),
        json={"job_description": "Python backend engineer"},
    )
    assert analysis.status_code == 200, analysis.text
    interview = client.post(
        "/api/v1/interviews",
        headers=auth_headers(token_a),
        json={"resume_id": resume["id"], "role": "swe"},
    )
    assert interview.status_code == 201, interview.text

    assert (
        client.get(f"/api/v1/resumes/{resume['id']}", headers=auth_headers(token_b)).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/interviews/{interview.json()['id']}", headers=auth_headers(token_b)
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/analyses/{analysis.json()['id']}/suggestions/{analysis.json()['suggestions'][0]['id']}",
            headers=auth_headers(token_b),
            json={"accept": True},
        ).status_code
        == 404
    )

    # A token containing another tenant's id must not let the user through.
    user_a = db.query(User).filter(User.email == account_a["user"]["email"]).one()
    forged, _ = create_access_token(user_id=user_a.id, college_id=college_b.id, role="student")
    assert client.get("/api/v1/auth/me", headers=auth_headers(forged)).status_code == 403

    # Same-college user also cannot read another student's interview.
    classmate = register(client, college_a.code, email=f"c{uuid.uuid4().hex[:6]}@example.com")
    assert (
        client.get(
            f"/api/v1/interviews/{interview.json()['id']}",
            headers=auth_headers(classmate["access_token"]),
        ).status_code
        == 404
    )


def test_officer_analytics_are_aggregate_and_consent_gated(client: TestClient, db) -> None:
    college = make_college(db)
    account = register(client, college.code, email=f"student{uuid.uuid4().hex[:6]}@example.com")
    token = account["access_token"]
    upload_resume(client, token, SAMPLE_RESUME)
    officer = make_user(
        db,
        college,
        role="officer",
        email=f"officer{uuid.uuid4().hex[:6]}@example.com",
        name="Placement Officer",
    )
    officer_token = login(client, officer.email)["access_token"]
    headers = auth_headers(officer_token)

    overview = client.get("/api/v1/officer/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    payload = overview.json()
    assert payload["aggregate_only"] is True
    row = next(r for r in payload["students"] if r["id"] == account["user"]["id"])
    assert row["consent"] is False
    assert row["display_name"] == "Hidden student"
    assert row["readiness"] is None

    consent = client.post(
        "/api/v1/auth/consent",
        headers=auth_headers(token),
        json={"share_analytics": True},
    )
    assert consent.status_code == 200
    updated = client.get("/api/v1/officer/overview", headers=headers).json()
    row = next(r for r in updated["students"] if r["id"] == account["user"]["id"])
    assert row["consent"] is True
    assert row["display_name"] != "Hidden student"

    # Students cannot reach officer analytics.
    assert client.get("/api/v1/officer/overview", headers=auth_headers(token)).status_code == 403


def test_officer_pdf_is_aggregate_only(client: TestClient, db) -> None:
    college = make_college(db)
    officer = make_user(db, college, role="officer")
    token = login(client, officer.email)["access_token"]
    response = client.get("/api/v1/officer/report.pdf", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_health(client: TestClient) -> None:
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/readyz").status_code == 200
