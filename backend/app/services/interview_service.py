"""Interview state machine, question generation and adaptive follow-ups."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ApiError, NotFoundError
from app.models.enums import ROUND_ORDER, InterviewStatus, Round, Speaker
from app.models.interview import Interview, InterviewTurn
from app.models.resume import Resume
from app.models.rubric import RubricVersion
from app.models.user import User
from app.prompts import prompt_version
from app.schemas.ai import InterviewQuestionAI
from app.services import gamification
from app.services.defaults import active_rubric, role_code
from app.services.embeddings import retrieve_questions
from app.services.llm.client import LLMClient
from app.services.safety import fence_untrusted, sanitize_text
from app.services.scoring import score_interview

QUESTIONS_PER_ROUND: dict[str, int] = {
    Round.PROJECT.value: 3,
    Round.TECHNICAL.value: 3,
    Round.HR.value: 2,
}
ROUND_TOPICS: dict[str, str] = {
    Round.PROJECT.value: "project",
    Round.TECHNICAL.value: "technical",
    Round.HR.value: "hr",
}
MAX_FOLLOWUPS = 2


@dataclass
class NextStep:
    question: InterviewTurn | None = None
    round_completed: str | None = None
    next_round: str | None = None
    finished: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)


def create_interview(
    db: Session,
    user: User,
    *,
    resume: Resume,
    role: str,
    target_role: str | None,
) -> Interview:
    rubric = active_rubric(db, user.college_id)
    code = role_code(target_role or user.target_role or role)
    interview = Interview(
        college_id=user.college_id,
        user_id=user.id,
        resume_id=resume.id,
        role=code if role in {"auto", ""} else role,
        status=InterviewStatus.ACTIVE.value,
        current_round=Round.PROJECT.value,
        current_index=0,
        rubric_version=rubric.version,
        prompt_version=prompt_version("interview_question"),
        model="mock",
    )
    db.add(interview)
    gamification.touch_streak(user)
    db.flush()
    return interview


def _project_names(resume: Resume | None) -> list[str]:
    if not resume or not resume.parsed_data:
        return []
    names = []
    for project in resume.parsed_data.get("projects", []) or []:
        name = str(project.get("name", "")).strip()
        if name and len(name) < 120:
            names.append(name)
    return names[:4]


def _asked_questions(db: Session, interview: Interview) -> list[str]:
    return [
        t.content
        for t in db.query(InterviewTurn)
        .filter(
            InterviewTurn.interview_id == interview.id,
            InterviewTurn.speaker == Speaker.INTERVIEWER.value,
        )
        .order_by(InterviewTurn.idx.asc())
        .all()
    ]


def _save_turn(
    db: Session,
    interview: Interview,
    *,
    speaker: Speaker,
    content: str,
    is_followup: bool = False,
    hint_used: bool = False,
) -> InterviewTurn:
    count = db.query(InterviewTurn).filter(InterviewTurn.interview_id == interview.id).count()
    turn = InterviewTurn(
        college_id=interview.college_id,
        interview_id=interview.id,
        idx=count,
        round=interview.current_round,
        speaker=speaker.value,
        content=content[:6000],
        is_followup=is_followup,
        hint_used=hint_used,
    )
    db.add(turn)
    db.flush()
    return turn


def generate_question(
    db: Session,
    user: User,
    interview: Interview,
    *,
    followup: bool,
    last_question: str = "",
    last_answer: str = "",
) -> tuple[InterviewTurn, InterviewQuestionAI]:
    resume = db.get(Resume, interview.resume_id) if interview.resume_id else None
    projects = _project_names(resume)
    candidates = retrieve_questions(
        db,
        college_id=interview.college_id,
        role=interview.role,
        topic=ROUND_TOPICS.get(interview.current_round, "technical"),
        query=f"{interview.role} {interview.current_round} {last_answer} {' '.join(projects)}",
        limit=4,
    )
    candidate_prompts = [q.prompt for q in candidates]
    asked = _asked_questions(db, interview)
    variables = {
        "role": interview.role,
        "round": interview.current_round,
        "resume_block": fence_untrusted(
            "RESUME_CONTEXT", resume.raw_text if resume else "No resume on file", max_chars=6000
        ),
        "project_context": fence_untrusted(
            "PROJECT_CONTEXT",
            "; ".join(projects) if projects else "No projects listed",
            max_chars=1200,
        ),
        "question_bank": "\n".join(f"- {q}" for q in candidate_prompts) or "- (no candidates)",
        "asked": "\n".join(f"- {q[:160]}" for q in asked[-9:]) or "- none",
        "candidates": candidate_prompts,
        "project_names": projects,
        "last_question": last_question,
        "last_answer": sanitize_text(last_answer, max_chars=3000),
        "previous_question_block": fence_untrusted(
            "PREVIOUS_QUESTION", last_question, max_chars=800
        ),
        "previous_answer_block": fence_untrusted("CANDIDATE_ANSWER", last_answer, max_chars=3000),
    }
    llm = LLMClient(db, user, feature="interview_question")
    prompt_id = "interview_followup" if followup else "interview_question"
    ai, meta = llm.structured(prompt_id, variables, InterviewQuestionAI, retries=1)
    turn = _save_turn(
        db, interview, speaker=Speaker.INTERVIEWER, content=ai.question, is_followup=followup
    )
    interview.model = meta.model
    interview.prompt_version = prompt_version(prompt_id)
    db.flush()
    return turn, ai


def start_interview(db: Session, user: User, interview: Interview) -> InterviewTurn:
    turn, _ = generate_question(db, user, interview, followup=False)
    return turn


def submit_answer(db: Session, user: User, interview: Interview, content: str) -> NextStep:
    if interview.status != InterviewStatus.ACTIVE.value:
        raise ApiError(409, "Interview is already complete", "interview_complete")
    answer = sanitize_text(content, max_chars=4000)
    if len(answer.strip()) < 2:
        raise ApiError(422, "Answer is too short", "answer_too_short")

    last_question = (
        db.query(InterviewTurn)
        .filter(
            InterviewTurn.interview_id == interview.id,
            InterviewTurn.speaker == Speaker.INTERVIEWER.value,
        )
        .order_by(InterviewTurn.idx.desc())
        .first()
    )
    _save_turn(db, interview, speaker=Speaker.CANDIDATE, content=answer)
    step = NextStep()

    word_count = len(answer.split())
    wants_followup = (
        interview.current_round == Round.PROJECT.value
        and interview.followups_asked < MAX_FOLLOWUPS
        and last_question is not None
        and not last_question.is_followup
        and word_count < 150
    )
    if wants_followup and last_question is not None:
        question, _ = generate_question(
            db,
            user,
            interview,
            followup=True,
            last_question=last_question.content,
            last_answer=answer,
        )
        interview.followups_asked += 1
        step.question = question
        return step

    if last_question is not None and not last_question.is_followup:
        interview.current_index += 1

    planned = QUESTIONS_PER_ROUND.get(interview.current_round, 3)
    if interview.current_index >= planned:
        step.round_completed = interview.current_round
        current_idx = ROUND_ORDER.index(Round(interview.current_round))
        if current_idx >= len(ROUND_ORDER) - 1:
            step.finished = True
            interview.current_index = planned
            db.flush()
            return step
        interview.current_round = ROUND_ORDER[current_idx + 1].value
        interview.current_index = 0
        step.next_round = interview.current_round

    question, _ = generate_question(db, user, interview, followup=False)
    step.question = question
    db.flush()
    return step


def finish_interview(
    db: Session,
    user: User,
    interview: Interview,
    rubric: RubricVersion,
    client: LLMClient | None = None,
) -> dict[str, Any]:
    turns = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.interview_id == interview.id)
        .order_by(InterviewTurn.idx.asc())
        .all()
    )
    result = score_interview(db, user, interview, rubric, turns, client=client)
    interview.status = InterviewStatus.COMPLETED.value
    interview.completed_at = datetime.now(UTC)
    if interview.started_at:
        start = interview.started_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        interview.duration_seconds = max(0, int((interview.completed_at - start).total_seconds()))
    gamification.touch_streak(user)
    gamification.award_xp(user, 60)
    db.flush()
    return result


def hint_for(db: Session, interview: Interview) -> str:
    last_question = (
        db.query(InterviewTurn)
        .filter(
            InterviewTurn.interview_id == interview.id,
            InterviewTurn.speaker == Speaker.INTERVIEWER.value,
        )
        .order_by(InterviewTurn.idx.desc())
        .first()
    )
    topic = last_question.content if last_question else "your answer"
    return (
        "Structure: one-line context, the decision you made, the trade-off, then the measurable "
        f"result. For “{topic[:90]}…”, name one concrete constraint and one thing you would change."
    )


def get_owned_interview(db: Session, user: User, interview_id: uuid.UUID) -> Interview:
    interview = (
        db.query(Interview)
        .filter(
            Interview.id == interview_id,
            Interview.user_id == user.id,
            Interview.college_id == user.college_id,
        )
        .one_or_none()
    )
    if interview is None:
        raise NotFoundError("Interview not found")
    return interview
