from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from tests.conftest import (
    SAMPLE_RESUME,
    analyze,
    auth_headers,
    make_college,
    register,
    upload_resume,
)


def test_full_three_round_interview_over_websocket(client: TestClient, db) -> None:
    college = make_college(db)
    account = register(client, college.code, email=f"flow{uuid.uuid4().hex[:6]}@example.com")
    token = account["access_token"]
    resume = upload_resume(client, token, SAMPLE_RESUME)
    analysis = analyze(client, token, resume["id"])
    assert analysis["score"] > 0

    rubric = client.get("/api/v1/rubrics/active", headers=auth_headers(token))
    assert rubric.status_code == 200
    assert len(rubric.json()["criteria"]) >= 4

    created = client.post(
        "/api/v1/interviews",
        headers=auth_headers(token),
        json={"resume_id": resume["id"], "role": "swe"},
    )
    assert created.status_code == 201, created.text
    interview_id = created.json()["id"]

    url = f"/api/v1/interviews/{interview_id}/ws?token={token}"
    with client.websocket_connect(url) as ws:
        session = ws.receive_json()
        assert session["type"] == "session"
        assert session["rubric"]["criteria"]

        message = ws.receive_json()
        while message["type"] not in {"question", "error"}:
            message = ws.receive_json()
        assert message["type"] == "question"

        finished = False
        scored: dict | None = None
        for _ in range(24):
            ws.send_json(
                {
                    "type": "answer",
                    "content": (
                        "I owned the backend for CampusRide. I designed the FastAPI service, "
                        "modelled Cloud SQL with PostgreSQL, added Redis caching and cut p95 "
                        "latency from 420ms to 260ms. I wrote integration tests for the Redis "
                        "failure path and monitored hit rate after release. The trade-off was "
                        "consistency versus latency, so I invalidated cache entries on writes."
                    ),
                }
            )
            while True:
                event = ws.receive_json()
                if event["type"] == "question":
                    break
                if event["type"] == "round_complete" and event.get("finished"):
                    finished = True
                    ws.send_json({"type": "finish"})
                    while True:
                        final = ws.receive_json()
                        if final["type"] == "scored":
                            scored = final
                            break
                        if final["type"] == "error":
                            raise AssertionError(final)
                    break
                if event["type"] == "error":
                    raise AssertionError(event)
            if finished:
                break

        assert scored is not None, "interview never returned a score"
        assert 0 <= scored["overall"] <= 100
        assert scored["rubric_version"] == "v1"
        assert scored["prompt_version"] == "v1"
        assert scored["criteria"]

    feedback = client.get(
        f"/api/v1/interviews/{interview_id}/feedback", headers=auth_headers(token)
    )
    assert feedback.status_code == 200, feedback.text
    payload = feedback.json()
    assert payload["transcript"]
    assert len(payload["criteria"]) >= 4
    assert all(criterion["improvement"] for criterion in payload["criteria"])
    assert payload["feedback"]["samples_used"] == 3

    dashboard = client.get("/api/v1/dashboard/student", headers=auth_headers(token))
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert body["interview_score"] is not None
    assert body["readiness"] > 0
    assert body["history"]

    usage = client.get("/api/v1/usage/me", headers=auth_headers(token))
    assert usage.status_code == 200
    assert usage.json()["tokens"] > 0


def test_hint_costs_xp_and_answer_validation(client: TestClient, db) -> None:
    college = make_college(db)
    account = register(client, college.code, email=f"hint{uuid.uuid4().hex[:6]}@example.com")
    token = account["access_token"]
    resume = upload_resume(client, token, SAMPLE_RESUME)
    created = client.post(
        "/api/v1/interviews",
        headers=auth_headers(token),
        json={"resume_id": resume["id"], "role": "swe"},
    )
    interview_id = created.json()["id"]
    before = client.get("/api/v1/auth/me", headers=auth_headers(token)).json()["xp"]
    with client.websocket_connect(f"/api/v1/interviews/{interview_id}/ws?token={token}") as ws:
        while ws.receive_json()["type"] != "question":
            pass
        ws.send_json({"type": "hint"})
        while True:
            message = ws.receive_json()
            if message["type"] == "hint":
                hint = message
                break
        assert hint["type"] == "hint"
        assert hint["xp_penalty"] == 5
    after = client.get("/api/v1/auth/me", headers=auth_headers(token)).json()["xp"]
    assert after == before - 5
