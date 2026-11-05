from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import settings
from app.core.errors import AIOutputError, BudgetExceededError
from app.models.enums import InterviewStatus, Round, Speaker
from app.models.interview import Interview, InterviewScore, InterviewTurn
from app.models.rubric import RubricVersion
from app.models.usage import UsageEvent
from app.models.user import User
from app.schemas.ai import RubricScoreAI
from app.services.cost import current_month
from app.services.defaults import DEFAULT_RUBRIC_VERSION
from app.services.llm.base import LLMMessage, LLMResult
from app.services.llm.client import LLMClient
from app.services.scoring import score_interview
from tests.conftest import (
    SAMPLE_RESUME,
    analyze,
    auth_headers,
    make_college,
    register,
    upload_resume,
)


class SequenceProvider:
    """Returns canned responses in order to exercise validation/retry."""

    name = "sequence"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        task: str = "",
        variables: dict | None = None,
    ) -> LLMResult:
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return LLMResult(
            text=self.responses[index],
            model="mock",
            input_tokens=100,
            output_tokens=50,
            provider=self.name,
        )


def _valid_score_payload(score: int = 7) -> dict:
    criteria = [
        ("clarity", 0.18),
        ("technical_depth", 0.24),
        ("problem_solving", 0.22),
        ("communication", 0.16),
        ("role_fit", 0.20),
    ]
    return {
        "criteria": [
            {
                "key": key,
                "score": score,
                "note": "Cited a concrete project trade-off and an outcome.",
                "improvement": "Add the measured result and the alternative you rejected.",
            }
            for key, _weight in criteria
        ],
        "strengths": ["Concrete project ownership"],
        "improvements": ["Quantify outcomes"],
        "summary": "Strong fundamentals with room for sharper evidence.",
    }


def _seed_interview(client: TestClient, db):
    college = make_college(db)
    account = register(client, college.code, email=f"sc{uuid.uuid4().hex[:6]}@example.com")
    token = account["access_token"]
    resume = upload_resume(client, token, SAMPLE_RESUME)
    analyze(client, token, resume["id"])
    interview_response = client.post(
        "/api/v1/interviews",
        headers=auth_headers(token),
        json={"resume_id": resume["id"], "role": "swe"},
    )
    assert interview_response.status_code == 201, interview_response.text
    interview_id = interview_response.json()["id"]
    db.expire_all()
    interview = db.get(Interview, uuid.UUID(interview_id))
    user = db.query(User).filter(User.email == account["user"]["email"]).one()
    rubric = (
        db.query(RubricVersion)
        .filter(
            RubricVersion.college_id == college.id,
            RubricVersion.version == DEFAULT_RUBRIC_VERSION,
        )
        .one()
    )
    questions = [
        "Walk me through your CampusRide project and your contribution.",
        "How did you reduce latency by 38%?",
        "Explain database indexing.",
        "How did you test the critical path?",
        "Tell me about a disagreement on your team.",
    ]
    answers = [
        "I owned the backend: I designed the FastAPI service, modelled the schema in PostgreSQL and added Redis caching, which reduced p95 latency from 420ms to 260ms.",
        "I measured the hot endpoint, found a repeated join, added a composite index and cached the read path. I invalidated on write and verified hit rate in staging.",
        "An index is a B-tree trading writes and storage for reads. It hurts with low selectivity or write-heavy tables because every insert updates it.",
        "I wrote integration tests against Postgres, covered the Redis-failure path and added structured logs before shipping.",
        "We disagreed on pagination. I showed the demo data exceeded one page, so we shipped cursor pagination and agreed on a review checklist.",
    ]
    turns: list[InterviewTurn] = []
    for index, (question, answer) in enumerate(zip(questions, answers, strict=True)):
        round_name = (
            Round.PROJECT.value
            if index < 2
            else Round.TECHNICAL.value
            if index < 4
            else Round.HR.value
        )
        turns.append(
            InterviewTurn(
                college_id=college.id,
                interview_id=interview.id,
                idx=index * 2,
                round=round_name,
                speaker=Speaker.INTERVIEWER.value,
                content=question,
            )
        )
        turns.append(
            InterviewTurn(
                college_id=college.id,
                interview_id=interview.id,
                idx=index * 2 + 1,
                round=round_name,
                speaker=Speaker.CANDIDATE.value,
                content=answer,
            )
        )
    db.add_all(turns)
    db.commit()
    return interview, user, rubric, turns


def test_schema_rejects_invalid_and_duplicate_criteria() -> None:
    payload = _valid_score_payload()
    payload["criteria"][0]["score"] = 11
    with pytest.raises(ValidationError):
        RubricScoreAI.model_validate(payload)

    duplicate = _valid_score_payload()
    duplicate["criteria"][1]["key"] = "clarity"
    with pytest.raises(ValidationError):
        RubricScoreAI.model_validate(duplicate)


def test_invalid_output_is_retried_then_accepted(client: TestClient, db) -> None:
    _, user = _seed_interview(client, db)[:2]
    provider = SequenceProvider(["not json at all", json.dumps(_valid_score_payload(6))])
    llm = LLMClient(db, user, "test", provider=provider)
    result, _ = llm.structured(
        "scoring",
        {
            "role": "swe",
            "rubric_block": "- clarity",
            "resume_block": "resume",
            "transcript_block": "transcript",
        },
        RubricScoreAI,
        retries=1,
    )
    assert provider.calls == 2
    assert result.criteria[0].score == 6


def test_exhausted_retries_raise(client: TestClient, db) -> None:
    _, user = _seed_interview(client, db)[:2]
    provider = SequenceProvider(["nope"])
    llm = LLMClient(db, user, "test", provider=provider)
    with pytest.raises(AIOutputError):
        llm.structured(
            "scoring",
            {
                "role": "swe",
                "rubric_block": "- clarity",
                "resume_block": "resume",
                "transcript_block": "transcript",
            },
            RubricScoreAI,
            retries=1,
        )


def test_median_of_three_samples_and_version_stamps(client: TestClient, db) -> None:
    interview, user, rubric, turns = _seed_interview(client, db)
    result = score_interview(db, user, interview, rubric, turns)
    db.commit()
    score = db.query(InterviewScore).filter(InterviewScore.interview_id == interview.id).one()
    assert len(score.samples) == 3
    assert result["overall"] == score.overall
    assert score.rubric_version == DEFAULT_RUBRIC_VERSION
    assert score.prompt_version == "v1"
    assert score.model == "mock"
    assert all(0 <= item["score"] <= 10 for item in score.medians)
    assert result["variance_flag"] is False


def test_high_variance_flags_human_review(client: TestClient, db) -> None:
    interview, user, rubric, turns = _seed_interview(client, db)
    provider = SequenceProvider(
        [
            json.dumps(_valid_score_payload(2)),
            json.dumps(_valid_score_payload(9)),
            json.dumps(_valid_score_payload(9)),
        ]
    )
    client_llm = LLMClient(db, user, "test", provider=provider)
    result = score_interview(db, user, interview, rubric, turns, client=client_llm)
    db.commit()
    assert result["variance_flag"] is True
    assert interview.needs_review is True
    assert (
        db.query(InterviewScore)
        .filter(InterviewScore.interview_id == interview.id)
        .one()
        .variance_flag
    )


def test_budget_is_enforced_before_llm_call(client: TestClient, db) -> None:
    _, user = _seed_interview(client, db)[:2]
    db.add(
        UsageEvent(
            college_id=user.college_id,
            user_id=user.id,
            feature="test",
            model="mock",
            input_tokens=10,
            output_tokens=10,
            cost_usd=settings.per_user_monthly_budget + 1,
            month=current_month(),
        )
    )
    db.commit()
    llm = LLMClient(
        db, user, "test", provider=SequenceProvider([json.dumps(_valid_score_payload())])
    )
    with pytest.raises(BudgetExceededError) as exc:
        llm.complete(
            "resume_analysis",
            {
                "target_role": "swe",
                "resume_block": "resume",
                "job_description_block": "jd",
                "resume_text": "resume",
                "job_description": "jd",
            },
        )
    assert exc.value.status_code == 402


def test_weights_are_recomputed_server_side(client: TestClient, db) -> None:
    interview, user, rubric, turns = _seed_interview(client, db)
    result = score_interview(db, user, interview, rubric, turns)
    expected = round(
        sum(item["score"] / 10 * item["weight"] * 100 for item in result["criteria"]), 1
    )
    assert result["overall"] == expected
    assert interview.status == InterviewStatus.ACTIVE.value
