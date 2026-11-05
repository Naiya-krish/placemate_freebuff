"""Rubric scoring: 3 low-temperature samples, schema validation, median, version stamps."""

from __future__ import annotations

import logging
import statistics
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AIOutputError
from app.models.interview import Interview, InterviewScore, InterviewTurn
from app.models.resume import Resume
from app.models.rubric import RubricVersion
from app.models.user import User
from app.prompts import prompt_version
from app.schemas.ai import RubricScoreAI
from app.services.defaults import rubric_weights
from app.services.llm.client import LLMClient
from app.services.safety import fence_untrusted, sanitize_text

logger = logging.getLogger(__name__)


def median_int(values: list[int]) -> int:
    if not values:
        return 0
    return int(round(statistics.median(values)))


def build_transcript(turns: list[InterviewTurn]) -> str:
    lines = []
    for turn in turns:
        if turn.speaker == "candidate":
            lines.append(f"Candidate: {turn.content}")
        elif turn.speaker == "interviewer":
            lines.append(f"Interviewer: {turn.content}")
    return "\n".join(lines)


def score_interview(
    db: Session,
    user: User,
    interview: Interview,
    rubric: RubricVersion,
    turns: list[InterviewTurn],
    client: LLMClient | None = None,
) -> dict[str, Any]:
    answers = [t.content for t in turns if t.speaker == "candidate" and t.content.strip()]
    if not answers:
        raise AIOutputError("No interview answers to score yet")
    transcript = build_transcript(turns)
    resume = db.get(Resume, interview.resume_id) if interview.resume_id else None
    variables = {
        "role": interview.role,
        "rubric_block": "\n".join(
            f"- {c['key']} ({c['label']}, weight {c['weight']}): {c['description']}"
            for c in rubric.criteria
        ),
        "resume_block": fence_untrusted(
            "RESUME_CONTEXT", resume.raw_text if resume else "No resume", max_chars=6000
        ),
        "transcript_block": fence_untrusted("TRANSCRIPT", transcript, max_chars=18_000),
        "rubric": rubric.criteria,
        "transcript": sanitize_text(transcript, max_chars=18_000),
        "answers": answers,
    }
    llm = client or LLMClient(db, user, feature="interview_scoring")
    samples: list[RubricScoreAI] = []
    meta_model = settings.llm_model_scoring
    errors = 0
    for _ in range(settings.scoring_samples):
        try:
            sample, meta = llm.structured(
                "scoring",
                variables,
                RubricScoreAI,
                tier="scoring",
                temperature=settings.scoring_temperature,
                retries=settings.scoring_max_retries,
            )
            samples.append(sample)
            meta_model = meta.model
        except AIOutputError:
            errors += 1
            logger.warning("scoring_sample_discarded interview=%s", interview.id)
    if not samples:
        raise AIOutputError("Scoring failed schema validation on every sample. Please retry.")

    weights = rubric_weights(rubric.criteria)
    by_key: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        for criterion in sample.criteria:
            if criterion.key in weights:
                by_key.setdefault(criterion.key, []).append(criterion.model_dump())
    if not by_key:
        raise AIOutputError("Scoring returned criteria that do not match the rubric.")

    medians: list[dict[str, Any]] = []
    criterion_scores: list[int] = []
    for rubric_criterion in rubric.criteria:
        key = str(rubric_criterion["key"])
        entries = by_key.get(key, [])
        if not entries:
            continue
        score = median_int([int(e["score"]) for e in entries])
        criterion_scores.append(score)
        reference = min(entries, key=lambda e: abs(int(e["score"]) - score))
        medians.append(
            {
                "key": key,
                "label": rubric_criterion["label"],
                "weight": float(rubric_criterion["weight"]),
                "score": score,
                "note": reference["note"],
                "improvement": reference["improvement"],
            }
        )

    overall = round(
        sum(float(m["score"]) / 10 * weights[m["key"]] * 100 for m in medians),
        1,
    )
    sample_overalls = [
        sum(int(c.score) / 10 * weights[c.key] * 100 for c in sample.criteria if c.key in weights)
        for sample in samples
    ]
    spread = round(max(sample_overalls) - min(sample_overalls), 1) if sample_overalls else 0.0
    variance_flag = spread > 15 or (errors > 0 and len(samples) < settings.scoring_samples)

    reference_sample = max(samples, key=lambda s: sum(1 for c in s.criteria if c.key in by_key))
    feedback = {
        "summary": reference_sample.summary,
        "strengths": reference_sample.strengths,
        "improvements": reference_sample.improvements,
        "samples_used": len(samples),
        "spread": spread,
        "needs_review": variance_flag,
        "rubric_label": rubric.label,
    }

    interview.overall_score = overall
    interview.rubric_scores = medians
    interview.feedback = feedback
    interview.variance_flag = variance_flag
    interview.needs_review = variance_flag
    interview.prompt_version = prompt_version("scoring")
    interview.rubric_version = rubric.version
    interview.model = meta_model

    score_row = (
        db.query(InterviewScore).filter(InterviewScore.interview_id == interview.id).one_or_none()
    )
    if score_row is None:
        score_row = InterviewScore(
            college_id=interview.college_id,
            interview_id=interview.id,
            overall=overall,
            rubric_version=rubric.version,
            prompt_version=prompt_version("scoring"),
            model=meta_model,
        )
        db.add(score_row)
    score_row.samples = [s.model_dump() for s in samples]
    score_row.medians = medians
    score_row.overall = overall
    score_row.spread = spread
    score_row.variance_flag = variance_flag
    score_row.needs_review = variance_flag
    score_row.rubric_version = rubric.version
    score_row.prompt_version = prompt_version("scoring")
    score_row.model = meta_model
    db.flush()
    return {
        "overall": overall,
        "criteria": medians,
        "feedback": feedback,
        "variance_flag": variance_flag,
        "samples_used": len(samples),
        "model": meta_model,
        "rubric_version": rubric.version,
        "prompt_version": prompt_version("scoring"),
    }
